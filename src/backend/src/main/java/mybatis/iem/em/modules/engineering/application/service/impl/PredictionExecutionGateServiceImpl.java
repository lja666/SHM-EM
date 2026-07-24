package mybatis.iem.em.modules.engineering.application.service.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import mybatis.iem.em.common.BusinessException;
import mybatis.iem.em.modules.engineering.application.dto.PredictionQuery;
import mybatis.iem.em.modules.engineering.application.service.PredictionExecutionGateService;
import mybatis.iem.em.modules.engineering.domain.model.PredictionBatch;
import mybatis.iem.em.modules.engineering.domain.model.PredictionCompleteness;
import mybatis.iem.em.modules.engineering.domain.model.PredictionDisplay;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionGate;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionMode;
import mybatis.iem.em.modules.engineering.domain.model.PredictionFeatureMapping;
import mybatis.iem.em.modules.engineering.domain.model.PredictionModel;
import mybatis.iem.em.modules.engineering.domain.model.PredictionRun;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.PredictionExecutionGateMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.PredictionMapper;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class PredictionExecutionGateServiceImpl implements PredictionExecutionGateService {
    private static final int MAX_REPORTED_MISSING_POINTS = 500;

    private final PredictionMapper predictionMapper;
    private final PredictionExecutionGateMapper gateMapper;
    private final CanonicalHashService canonicalHashService;
    private final ObjectMapper objectMapper;

    public PredictionExecutionGateServiceImpl(PredictionMapper predictionMapper,
                                              PredictionExecutionGateMapper gateMapper,
                                              CanonicalHashService canonicalHashService,
                                              ObjectMapper objectMapper) {
        this.predictionMapper = predictionMapper;
        this.gateMapper = gateMapper;
        this.canonicalHashService = canonicalHashService;
        this.objectMapper = objectMapper;
    }

    @Override
    public PredictionExecutionGate evaluate(Long batchId, PredictionExecutionMode mode, LocalDateTime referenceTime) {
        PredictionExecutionGate gate = inspect(batchId, mode, referenceTime);
        serializeLists(gate);
        gateMapper.insert(gate);
        return gate;
    }

    @Override
    public PredictionExecutionGate inspect(Long batchId, PredictionExecutionMode mode, LocalDateTime referenceTime) {
        PredictionBatch batch = batchId == null ? null : predictionMapper.selectBatchById(batchId);
        if (batch == null) {
            throw new BusinessException("Prediction batch not found: " + batchId);
        }
        PredictionExecutionMode effectiveMode = mode == null ? PredictionExecutionMode.OPERATIONAL : mode;
        List<PredictionModel> models = contractModels(batch.getProjectId());
        List<PredictionFeatureMapping> features = contractFeatures(batch.getProjectId());
        List<PredictionRun> runs = safe(predictionMapper.selectRunsByBatch(batchId));
        PredictionQuery resultQuery = new PredictionQuery();
        resultQuery.setBatchId(batchId);
        resultQuery.setLimit(50000);
        List<PredictionDisplay> results = safe(predictionMapper.selectSeries(resultQuery, 50000));

        PredictionExecutionGate gate = new PredictionExecutionGate();
        gate.setBatchId(batch.getId());
        gate.setProjectId(batch.getProjectId());
        gate.setBatchCode(batch.getBatchCode());
        gate.setExecutionMode(effectiveMode.name());
        gate.setEvaluatedAt(LocalDateTime.now());
        gate.setExpectedSteps(resolveExpectedSteps(models, gate));
        gate.setContractVersion(resolveContractVersion(models, batch));
        gate.setContractFingerprint(contractFingerprint(models, features));

        Map<String, PredictionModel> expectedModels = expectedModels(models);
        Map<String, PredictionRun> actualRuns = actualRuns(runs, gate);
        validateModels(batch, expectedModels, actualRuns, gate);

        Map<String, Set<String>> expectedFeatures = expectedFeatures(expectedModels, features, gate);
        validateFeaturesAndTimeline(batch, expectedModels, expectedFeatures, results, effectiveMode, gate);
        validateArtifacts(batch, expectedModels, actualRuns, gate);
        validateFreshness(batch, models, effectiveMode, referenceTime, gate);

        boolean batchSuccessful = "success".equalsIgnoreCase(batch.getStatus());
        if (!batchSuccessful) {
            gate.getIssues().add("Batch status is not success");
        }
        gate.setExecutionEligible(batchSuccessful
                && Boolean.TRUE.equals(gate.getModelSetValid())
                && Boolean.TRUE.equals(gate.getFeatureSetValid())
                && Boolean.TRUE.equals(gate.getTimelineValid())
                && Boolean.TRUE.equals(gate.getQualityValid())
                && Boolean.TRUE.equals(gate.getArtifactHashValid())
                && Boolean.TRUE.equals(gate.getFreshnessValid()));
        gate.setGateHash(gateHash(batch, gate));
        return gate;
    }

    @Override
    public PredictionExecutionGate latest(Long batchId, PredictionExecutionMode mode) {
        PredictionExecutionMode effectiveMode = mode == null ? PredictionExecutionMode.OPERATIONAL : mode;
        PredictionExecutionGate gate = gateMapper.selectLatest(batchId, effectiveMode.name());
        if (gate == null) {
            return inspect(batchId, effectiveMode, null);
        }
        hydrateLists(gate);
        return gate;
    }

    private List<PredictionModel> contractModels(Long projectId) {
        PredictionQuery query = new PredictionQuery();
        query.setProjectId(projectId);
        query.setLimit(500);
        return safe(predictionMapper.selectModels(query, 500));
    }

    private List<PredictionFeatureMapping> contractFeatures(Long projectId) {
        PredictionQuery query = new PredictionQuery();
        query.setProjectId(projectId);
        query.setLimit(50000);
        return safe(predictionMapper.selectFeatures(query, 50000)).stream()
                .filter(item -> item.getRequired() == null || item.getRequired() == 1)
                .filter(item -> isBlank(item.getFeatureRole()) || "model_input".equalsIgnoreCase(item.getFeatureRole()))
                .filter(item -> item.getPredictionTarget() != null && item.getPredictionTarget() == 1)
                .collect(Collectors.toList());
    }

    private Map<String, PredictionModel> expectedModels(List<PredictionModel> models) {
        Map<String, PredictionModel> result = new LinkedHashMap<String, PredictionModel>();
        models.stream()
                .sorted(Comparator.comparing(PredictionModel::getModelCode, Comparator.nullsLast(String::compareToIgnoreCase)))
                .forEach(model -> result.put(modelKey(model.getModelCode(), model.getModelVersion()), model));
        return result;
    }

    private Map<String, PredictionRun> actualRuns(List<PredictionRun> runs, PredictionExecutionGate gate) {
        Map<String, PredictionRun> result = new LinkedHashMap<String, PredictionRun>();
        for (PredictionRun run : runs) {
            String key = modelKey(run.getModelCode(), run.getModelVersion());
            if (result.containsKey(key)) {
                gate.getIssues().add("Duplicate prediction run for model " + key);
            }
            result.put(key, run);
        }
        return result;
    }

    private void validateModels(PredictionBatch batch,
                                Map<String, PredictionModel> expected,
                                Map<String, PredictionRun> actual,
                                PredictionExecutionGate gate) {
        Set<String> missing = new LinkedHashSet<String>(expected.keySet());
        missing.removeAll(actual.keySet());
        Set<String> unexpected = new LinkedHashSet<String>(actual.keySet());
        unexpected.removeAll(expected.keySet());
        gate.getMissingModels().addAll(missing);
        gate.getUnexpectedModels().addAll(unexpected);
        gate.setExpectedModelCount(expected.size());
        gate.setActualModelCount(actual.size());
        gate.setSuccessfulModelCount((int) actual.values().stream()
                .filter(run -> "success".equalsIgnoreCase(run.getStatus()))
                .count());
        if (expected.isEmpty()) gate.getIssues().add("No active model contract is registered for the project");
        if (!missing.isEmpty()) gate.getIssues().add("Required model runs are missing");
        if (!unexpected.isEmpty()) gate.getIssues().add("Prediction batch contains models outside the active contract");
        if (gate.getSuccessfulModelCount() < expected.size()) gate.getIssues().add("One or more required model runs are not successful");
        if (batch.getModelCount() == null || batch.getModelCount() != expected.size()) {
            gate.getIssues().add("Batch model count does not match the active model contract");
        }
        boolean duplicateRuns = gate.getIssues().stream().anyMatch(issue -> issue.startsWith("Duplicate prediction run"));
        gate.setModelSetValid(!expected.isEmpty()
                && missing.isEmpty()
                && unexpected.isEmpty()
                && !duplicateRuns
                && gate.getSuccessfulModelCount() == expected.size()
                && batch.getModelCount() != null
                && batch.getModelCount() == expected.size());
    }

    private Map<String, Set<String>> expectedFeatures(Map<String, PredictionModel> models,
                                                      List<PredictionFeatureMapping> features,
                                                      PredictionExecutionGate gate) {
        Map<String, Set<String>> result = new LinkedHashMap<String, Set<String>>();
        for (Map.Entry<String, PredictionModel> entry : models.entrySet()) {
            PredictionModel model = entry.getValue();
            Set<String> modelFeatures = features.stream()
                    .filter(feature -> belongsToModel(feature, model))
                    .map(PredictionFeatureMapping::getFeatureCode)
                    .filter(code -> !isBlank(code))
                    .collect(Collectors.toCollection(LinkedHashSet::new));
            if (modelFeatures.isEmpty()) {
                gate.getIssues().add("No required feature contract is registered for model " + entry.getKey());
            }
            result.put(entry.getKey(), modelFeatures);
        }
        return result;
    }

    private boolean belongsToModel(PredictionFeatureMapping feature, PredictionModel model) {
        if (feature.getModelId() != null && model.getId() != null) {
            return feature.getModelId().equals(model.getId());
        }
        return !isBlank(feature.getTargetType())
                && !isBlank(model.getTargetType())
                && feature.getTargetType().equalsIgnoreCase(model.getTargetType());
    }

    private void validateFeaturesAndTimeline(PredictionBatch batch,
                                             Map<String, PredictionModel> models,
                                             Map<String, Set<String>> expectedFeatures,
                                             List<PredictionDisplay> results,
                                             PredictionExecutionMode mode,
                                             PredictionExecutionGate gate) {
        int expectedSteps = gate.getExpectedSteps();
        int stepMinutes = batch.getTimeStepMinutes() == null ? 0 : batch.getTimeStepMinutes();
        Map<String, Set<Integer>> actualSteps = new LinkedHashMap<String, Set<Integer>>();
        Set<String> expectedFeatureKeys = new LinkedHashSet<String>();
        Set<String> actualFeatureKeys = new LinkedHashSet<String>();
        Set<String> unexpectedFeatureKeys = new LinkedHashSet<String>();
        int invalidTimestampCount = 0;
        int qualityIssueCount = 0;
        int duplicatePointCount = 0;

        for (Map.Entry<String, Set<String>> entry : expectedFeatures.entrySet()) {
            for (String feature : entry.getValue()) expectedFeatureKeys.add(entry.getKey() + ":" + feature);
        }
        for (PredictionDisplay row : results) {
            String modelKey = modelKey(row.getModelCode(), row.getModelVersion());
            String featureKey = modelKey + ":" + text(row.getFeatureCode(), "<missing>");
            if (!expectedFeatureKeys.contains(featureKey)) {
                unexpectedFeatureKeys.add(featureKey);
                continue;
            }
            actualFeatureKeys.add(featureKey);
            Integer step = row.getStep();
            Set<Integer> steps = actualSteps.computeIfAbsent(featureKey, key -> new HashSet<Integer>());
            if (step != null && !steps.add(step)) duplicatePointCount++;
            if (!validTimelinePoint(batch, row, expectedSteps, stepMinutes)) invalidTimestampCount++;
            if (!isAcceptedQuality(row.getQualityFlag(), mode)) qualityIssueCount++;
        }

        Set<String> missingFeatureKeys = new LinkedHashSet<String>(expectedFeatureKeys);
        missingFeatureKeys.removeAll(actualFeatureKeys);
        gate.getMissingFeatures().addAll(missingFeatureKeys);
        gate.getUnexpectedFeatures().addAll(unexpectedFeatureKeys);
        int actualPointCount = 0;
        Map<String, PredictionCompleteness.TargetCompleteness> targets = new LinkedHashMap<String, PredictionCompleteness.TargetCompleteness>();
        for (Map.Entry<String, Set<String>> modelEntry : expectedFeatures.entrySet()) {
            PredictionModel model = models.get(modelEntry.getKey());
            String target = text(model == null ? null : model.getTargetType(), modelEntry.getKey());
            PredictionCompleteness.TargetCompleteness targetRow = new PredictionCompleteness.TargetCompleteness();
            targetRow.setTargetType(target);
            targetRow.setFeatureCount(modelEntry.getValue().size());
            targetRow.setExpectedPointCount(modelEntry.getValue().size() * expectedSteps);
            targetRow.setActualPointCount(0);
            targetRow.setCoveredSteps(0);
            targetRow.setQualityIssueCount(0);
            Set<Integer> targetCoveredSteps = new HashSet<Integer>();
            for (String feature : modelEntry.getValue()) {
                String key = modelEntry.getKey() + ":" + feature;
                Set<Integer> steps = actualSteps.getOrDefault(key, Collections.<Integer>emptySet());
                for (int step = 1; step <= expectedSteps; step++) {
                    if (steps.contains(step)) {
                        actualPointCount++;
                        targetRow.setActualPointCount(targetRow.getActualPointCount() + 1);
                        targetCoveredSteps.add(step);
                    } else if (gate.getMissingTimelinePoints().size() < MAX_REPORTED_MISSING_POINTS) {
                        String missingPoint = key + ":step-" + step;
                        gate.getMissingTimelinePoints().add(missingPoint);
                        if (targetRow.getMissingPoints().size() < 200) targetRow.getMissingPoints().add(feature + ":" + step);
                    }
                }
            }
            targetRow.setCoveredSteps(targetCoveredSteps.size());
            targetRow.setMissingPointCount(Math.max(0, targetRow.getExpectedPointCount() - targetRow.getActualPointCount()));
            targetRow.setCompletenessPercent(percent(targetRow.getActualPointCount(), targetRow.getExpectedPointCount()));
            targetRow.setComplete(targetRow.getExpectedPointCount() > 0 && targetRow.getMissingPointCount() == 0);
            targets.put(modelEntry.getKey(), targetRow);
        }
        gate.getTargets().addAll(targets.values());
        gate.setExpectedFeatureCount(expectedFeatureKeys.size());
        gate.setActualFeatureCount(actualFeatureKeys.size());
        gate.setExpectedPointCount(expectedFeatureKeys.size() * expectedSteps);
        gate.setActualPointCount(actualPointCount);
        gate.setMissingPointCount(Math.max(0, gate.getExpectedPointCount() - actualPointCount));
        gate.setInvalidTimestampCount(invalidTimestampCount + duplicatePointCount);
        gate.setQualityIssueCount(qualityIssueCount);
        if (!missingFeatureKeys.isEmpty()) gate.getIssues().add("Required prediction features are missing");
        if (!unexpectedFeatureKeys.isEmpty()) gate.getIssues().add("Prediction results contain features outside the active contract");
        if (gate.getMissingPointCount() > 0) {
            gate.getIssues().add("The required " + expectedSteps + "-step prediction timeline is incomplete");
        }
        if (invalidTimestampCount > 0) gate.getIssues().add("Prediction timestamps or horizons do not match the batch timeline");
        if (duplicatePointCount > 0) gate.getIssues().add("Prediction results contain duplicate model-feature-step points");
        if (qualityIssueCount > 0) gate.getIssues().add("Prediction results contain quality flags requiring review");
        if (batch.getFeatureCount() == null || batch.getFeatureCount() != expectedFeatureKeys.size()) {
            gate.getIssues().add("Batch feature count does not match the active feature contract");
        }
        gate.setFeatureSetValid(!expectedFeatureKeys.isEmpty()
                && missingFeatureKeys.isEmpty()
                && unexpectedFeatureKeys.isEmpty()
                && batch.getFeatureCount() != null
                && batch.getFeatureCount() == expectedFeatureKeys.size());
        gate.setTimelineValid(gate.getExpectedSteps() > 0
                && batch.getRollingSteps() != null
                && batch.getRollingSteps().equals(gate.getExpectedSteps())
                && models.values().stream().allMatch(model -> model.getExpectedSteps() != null
                    && model.getExpectedSteps().equals(gate.getExpectedSteps())
                    && model.getTimeStepMinutes() != null
                    && model.getTimeStepMinutes().equals(batch.getTimeStepMinutes()))
                && gate.getMissingPointCount() == 0
                && gate.getInvalidTimestampCount() == 0);
        gate.setQualityValid(qualityIssueCount == 0);
    }

    private boolean validTimelinePoint(PredictionBatch batch, PredictionDisplay row, int expectedSteps, int stepMinutes) {
        if (row.getStep() == null || row.getStep() < 1 || row.getStep() > expectedSteps
                || batch.getBaseTime() == null || row.getBaseTime() == null || row.getFutureTime() == null
                || stepMinutes <= 0) {
            return false;
        }
        LocalDateTime expectedTime = batch.getBaseTime().plusMinutes((long) row.getStep() * stepMinutes);
        long seconds = Math.abs(Duration.between(expectedTime, row.getFutureTime()).getSeconds());
        return batch.getBaseTime().equals(row.getBaseTime())
                && seconds <= 1
                && row.getHorizonMinutes() != null
                && row.getHorizonMinutes() == row.getStep() * stepMinutes;
    }

    private void validateArtifacts(PredictionBatch batch,
                                   Map<String, PredictionModel> models,
                                   Map<String, PredictionRun> runs,
                                   PredictionExecutionGate gate) {
        boolean valid = !isBlank(batch.getInputHash()) && !isBlank(batch.getOutputHash());
        if (!valid) gate.getIssues().add("Batch input or output hash is missing");
        for (Map.Entry<String, PredictionModel> entry : models.entrySet()) {
            PredictionModel model = entry.getValue();
            PredictionRun run = runs.get(entry.getKey());
            if (run == null) {
                valid = false;
                continue;
            }
            if (isBlank(model.getArtifactHash()) || !model.getArtifactHash().equalsIgnoreCase(text(run.getArtifactHash(), ""))) {
                valid = false;
                gate.getIssues().add("Artifact hash mismatch for model " + entry.getKey());
            }
            if (isBlank(model.getPreprocessorHash())
                    || !model.getPreprocessorHash().equalsIgnoreCase(text(run.getPreprocessorHash(), ""))) {
                valid = false;
                gate.getIssues().add("Preprocessor hash mismatch for model " + entry.getKey());
            }
            if (isBlank(model.getInferenceScriptHash())
                    || !model.getInferenceScriptHash().equalsIgnoreCase(text(run.getInferenceScriptHash(), ""))) {
                valid = false;
                gate.getIssues().add("Inference script hash mismatch for model " + entry.getKey());
            }
            if (!nullableHashesEqual(model.getBestParamsHash(), run.getBestParamsHash())) {
                valid = false;
                gate.getIssues().add("Best-parameter hash mismatch for model " + entry.getKey());
            }
            if (isBlank(model.getRuntimeManifestHash())
                    || !model.getRuntimeManifestHash().equalsIgnoreCase(text(run.getRuntimeManifestHash(), ""))) {
                valid = false;
                gate.getIssues().add("Runtime manifest hash mismatch for model " + entry.getKey());
            }
            if (isBlank(model.getEnvironmentDigest())
                    || !model.getEnvironmentDigest().equalsIgnoreCase(text(run.getEnvironmentDigest(), ""))) {
                valid = false;
                gate.getIssues().add("Environment digest mismatch for model " + entry.getKey());
            }
            if (isBlank(model.getArtifactBundleHash())
                    || !model.getArtifactBundleHash().equalsIgnoreCase(text(run.getArtifactBundleHash(), ""))) {
                valid = false;
                gate.getIssues().add("Artifact bundle hash mismatch for model " + entry.getKey());
            }
            if (isBlank(model.getInputSchemaHash()) || !model.getInputSchemaHash().equalsIgnoreCase(text(run.getInputSchemaHash(), ""))) {
                valid = false;
                gate.getIssues().add("Input schema hash mismatch for model " + entry.getKey());
            }
            if (isBlank(run.getResultHash())) {
                valid = false;
                gate.getIssues().add("Result hash is missing for model " + entry.getKey());
            }
            if (run.getRollingSteps() == null || run.getRollingSteps() != gate.getExpectedSteps()) {
                valid = false;
                gate.getIssues().add("Run step count does not match the model contract for " + entry.getKey());
            }
        }
        gate.setArtifactHashValid(valid);
    }

    private void validateFreshness(PredictionBatch batch,
                                   List<PredictionModel> models,
                                   PredictionExecutionMode mode,
                                   LocalDateTime requestedReferenceTime,
                                   PredictionExecutionGate gate) {
        LocalDateTime referenceTime = requestedReferenceTime;
        if (referenceTime == null) {
            referenceTime = mode == PredictionExecutionMode.OPERATIONAL ? LocalDateTime.now() : batch.getBaseTime();
        }
        gate.setReferenceTime(referenceTime);
        if (batch.getBaseTime() == null || referenceTime == null) {
            gate.setBaseTimeAgeMinutes(null);
            gate.setFreshnessValid(false);
            gate.getIssues().add("Batch base time or gate reference time is missing");
            return;
        }
        long age = Duration.between(batch.getBaseTime(), referenceTime).toMinutes();
        int maxAge = mode == PredictionExecutionMode.OPERATIONAL
                ? models.stream().map(PredictionModel::getMaxOperationalAgeMinutes).filter(value -> value != null && value > 0).min(Integer::compareTo).orElse(15)
                : (batch.getHorizonMinutes() == null || batch.getHorizonMinutes() <= 0 ? 120 : batch.getHorizonMinutes());
        boolean valid = age >= 0 && age <= maxAge;
        gate.setBaseTimeAgeMinutes(age);
        gate.setMaxAgeMinutes(maxAge);
        gate.setFreshnessValid(valid);
        if (!valid) {
            gate.getIssues().add(mode == PredictionExecutionMode.OPERATIONAL
                    ? "Prediction batch is stale for operational execution"
                    : "Replay reference time is outside the prediction horizon");
        }
    }

    private int resolveExpectedSteps(List<PredictionModel> models, PredictionExecutionGate gate) {
        Set<Integer> configured = models.stream()
                .map(PredictionModel::getExpectedSteps)
                .filter(value -> value != null && value > 0)
                .collect(Collectors.toCollection(LinkedHashSet::new));
        if (configured.size() != 1) {
            gate.getIssues().add("All active model contracts must declare one consistent positive forecast-step count");
        }
        return configured.size() == 1 ? configured.iterator().next() : 0;
    }

    private String resolveContractVersion(List<PredictionModel> models, PredictionBatch batch) {
        Set<String> versions = models.stream().map(PredictionModel::getContractVersion).filter(value -> !isBlank(value)).collect(Collectors.toSet());
        if (versions.size() == 1) return versions.iterator().next();
        return text(batch.getFeatureMappingVersion(), "unversioned");
    }

    private String contractFingerprint(List<PredictionModel> models, List<PredictionFeatureMapping> features) {
        List<Map<String, Object>> modelContract = new ArrayList<Map<String, Object>>();
        models.stream().sorted(Comparator.comparing(PredictionModel::getModelCode)).forEach(model -> {
            Map<String, Object> row = new LinkedHashMap<String, Object>();
            row.put("id", model.getId());
            row.put("code", model.getModelCode());
            row.put("version", model.getModelVersion());
            row.put("target", model.getTargetType());
            row.put("artifactHash", model.getArtifactHash());
            row.put("preprocessorHash", model.getPreprocessorHash());
            row.put("inferenceScriptHash", model.getInferenceScriptHash());
            row.put("bestParamsHash", model.getBestParamsHash());
            row.put("runtimeManifestHash", model.getRuntimeManifestHash());
            row.put("environmentDigest", model.getEnvironmentDigest());
            row.put("artifactBundleHash", model.getArtifactBundleHash());
            row.put("inputSchemaHash", model.getInputSchemaHash());
            row.put("expectedSteps", model.getExpectedSteps());
            row.put("timeStepMinutes", model.getTimeStepMinutes());
            modelContract.add(row);
        });
        List<Map<String, Object>> featureContract = new ArrayList<Map<String, Object>>();
        features.stream().sorted(Comparator.comparing(PredictionFeatureMapping::getFeatureCode)).forEach(feature -> {
            Map<String, Object> row = new LinkedHashMap<String, Object>();
            row.put("modelId", feature.getModelId());
            row.put("target", feature.getTargetType());
            row.put("feature", feature.getFeatureCode());
            row.put("sourceMetric", feature.getSourceMetricCode());
            row.put("sourceRegistry", feature.getSourceRegistryCode());
            row.put("valueMode", feature.getInputValueMode());
            row.put("schemaVersion", feature.getSchemaVersion());
            row.put("predictionTarget", feature.getPredictionTarget());
            featureContract.add(row);
        });
        Map<String, Object> contract = new LinkedHashMap<String, Object>();
        contract.put("models", modelContract);
        contract.put("features", featureContract);
        return canonicalHashService.sha256Canonical(contract);
    }

    private String gateHash(PredictionBatch batch, PredictionExecutionGate gate) {
        Map<String, Object> state = new LinkedHashMap<String, Object>();
        state.put("batchId", batch.getId());
        state.put("mode", gate.getExecutionMode());
        state.put("contractFingerprint", gate.getContractFingerprint());
        state.put("inputHash", batch.getInputHash());
        state.put("outputHash", batch.getOutputHash());
        state.put("modelSetValid", gate.getModelSetValid());
        state.put("featureSetValid", gate.getFeatureSetValid());
        state.put("timelineValid", gate.getTimelineValid());
        state.put("qualityValid", gate.getQualityValid());
        state.put("artifactHashValid", gate.getArtifactHashValid());
        state.put("freshnessValid", gate.getFreshnessValid());
        state.put("executionEligible", gate.getExecutionEligible());
        state.put("issues", gate.getIssues());
        return canonicalHashService.sha256Canonical(state);
    }

    private void serializeLists(PredictionExecutionGate gate) {
        try {
            gate.setIssuesJson(objectMapper.writeValueAsString(gate.getIssues()));
            gate.setMissingModelsJson(objectMapper.writeValueAsString(gate.getMissingModels()));
            gate.setUnexpectedModelsJson(objectMapper.writeValueAsString(gate.getUnexpectedModels()));
            gate.setMissingFeaturesJson(objectMapper.writeValueAsString(gate.getMissingFeatures()));
            gate.setUnexpectedFeaturesJson(objectMapper.writeValueAsString(gate.getUnexpectedFeatures()));
            gate.setMissingTimelinePointsJson(objectMapper.writeValueAsString(gate.getMissingTimelinePoints()));
            gate.setTargetSummaryJson(objectMapper.writeValueAsString(gate.getTargets()));
        } catch (Exception ex) {
            throw new IllegalStateException("Failed to serialize prediction execution gate", ex);
        }
    }

    private void hydrateLists(PredictionExecutionGate gate) {
        gate.setIssues(readList(gate.getIssuesJson(), new TypeReference<List<String>>() {}));
        gate.setMissingModels(readList(gate.getMissingModelsJson(), new TypeReference<List<String>>() {}));
        gate.setUnexpectedModels(readList(gate.getUnexpectedModelsJson(), new TypeReference<List<String>>() {}));
        gate.setMissingFeatures(readList(gate.getMissingFeaturesJson(), new TypeReference<List<String>>() {}));
        gate.setUnexpectedFeatures(readList(gate.getUnexpectedFeaturesJson(), new TypeReference<List<String>>() {}));
        gate.setMissingTimelinePoints(readList(gate.getMissingTimelinePointsJson(), new TypeReference<List<String>>() {}));
        gate.setTargets(readList(gate.getTargetSummaryJson(), new TypeReference<List<PredictionCompleteness.TargetCompleteness>>() {}));
    }

    private <T> T readList(String json, TypeReference<T> type) {
        try {
            return isBlank(json) ? objectMapper.readValue("[]", type) : objectMapper.readValue(json, type);
        } catch (Exception ex) {
            throw new IllegalStateException("Failed to read persisted prediction execution gate", ex);
        }
    }

    private BigDecimal percent(int actual, int expected) {
        if (expected <= 0) return BigDecimal.ZERO;
        return BigDecimal.valueOf(actual).multiply(BigDecimal.valueOf(100)).divide(BigDecimal.valueOf(expected), 1, RoundingMode.HALF_UP);
    }

    private boolean isAcceptedQuality(String qualityFlag, PredictionExecutionMode mode) {
        if (isBlank(qualityFlag)) {
            return mode == PredictionExecutionMode.REPLAY;
        }
        return "normal".equalsIgnoreCase(qualityFlag) || "ok".equalsIgnoreCase(qualityFlag);
    }

    private String modelKey(String code, String version) {
        return text(code, "<missing-model>") + "@" + text(version, "<missing-version>");
    }

    private String text(String value, String fallback) {
        return isBlank(value) ? fallback : value.trim();
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private boolean nullableHashesEqual(String expected, String actual) {
        if (isBlank(expected) && isBlank(actual)) return true;
        return !isBlank(expected) && expected.equalsIgnoreCase(text(actual, ""));
    }

    private <T> List<T> safe(List<T> rows) {
        return rows == null ? Collections.<T>emptyList() : rows;
    }
}
