package mybatis.iem.em.modules.engineering.application.service.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import mybatis.iem.em.modules.engineering.application.dto.PredictionQuery;
import mybatis.iem.em.modules.engineering.domain.model.PredictionBatch;
import mybatis.iem.em.modules.engineering.domain.model.PredictionDisplay;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionGate;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionMode;
import mybatis.iem.em.modules.engineering.domain.model.PredictionFeatureMapping;
import mybatis.iem.em.modules.engineering.domain.model.PredictionModel;
import mybatis.iem.em.modules.engineering.domain.model.PredictionRun;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.PredictionExecutionGateMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.PredictionMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

public class PredictionExecutionGateServiceImplTest {
    private PredictionMapper predictionMapper;
    private PredictionExecutionGateServiceImpl service;
    private PredictionBatch batch;
    private PredictionModel model;
    private PredictionFeatureMapping feature;
    private PredictionRun run;
    private PersistedPredictionIntegrityHashService integrityHashService;

    @BeforeEach
    public void setUp() {
        predictionMapper = mock(PredictionMapper.class);
        PredictionExecutionGateMapper gateMapper = mock(PredictionExecutionGateMapper.class);
        ObjectMapper objectMapper = new ObjectMapper();
        integrityHashService = new PersistedPredictionIntegrityHashService(objectMapper);
        service = new PredictionExecutionGateServiceImpl(
                predictionMapper,
                gateMapper,
                new CanonicalHashService(objectMapper),
                integrityHashService,
                objectMapper);
        doAnswer(invocation -> {
            PredictionExecutionGate gate = invocation.getArgument(0);
            gate.setId(100L);
            return 1;
        }).when(gateMapper).insert(any(PredictionExecutionGate.class));

        LocalDateTime baseTime = LocalDateTime.of(2026, 6, 24, 10, 0);
        batch = new PredictionBatch();
        batch.setId(1L);
        batch.setProjectId(1L);
        batch.setBatchCode("BATCH-1");
        batch.setBaseTime(baseTime);
        batch.setTimeStepMinutes(3);
        batch.setHorizonMinutes(120);
        batch.setRollingSteps(40);
        batch.setModelCount(1);
        batch.setFeatureCount(1);
        batch.setInputHash("input-hash");
        batch.setOutputHash("output-hash");
        batch.setStatus("success");

        model = new PredictionModel();
        model.setId(10L);
        model.setProjectId(1L);
        model.setModelCode("YD");
        model.setModelVersion("v1");
        model.setTargetType("YD");
        model.setArtifactHash("artifact-hash");
        model.setPreprocessorHash("preprocessor-hash");
        model.setInferenceScriptHash("script-hash");
        model.setRuntimeManifestHash("runtime-manifest-hash");
        model.setEnvironmentDigest("environment-digest");
        model.setArtifactBundleHash("bundle-hash");
        model.setInputSchemaHash("schema-hash");
        model.setContractVersion("contract-v1");
        model.setExpectedSteps(40);
        model.setTimeStepMinutes(3);
        model.setMaxOperationalAgeMinutes(15);

        feature = feature("point1_0.8YD_value");

        run = new PredictionRun();
        run.setId(20L);
        run.setModelId(10L);
        run.setModelCode("YD");
        run.setModelVersion("v1");
        run.setTargetType("YD");
        run.setArtifactHash("artifact-hash");
        run.setPreprocessorHash("preprocessor-hash");
        run.setInferenceScriptHash("script-hash");
        run.setRuntimeManifestHash("runtime-manifest-hash");
        run.setEnvironmentDigest("environment-digest");
        run.setArtifactBundleHash("bundle-hash");
        run.setInputSchemaHash("schema-hash");
        run.setResultHash("result-hash");
        run.setPersistedResultHashVersion(PersistedPredictionIntegrityHashService.RESULT_HASH_VERSION);
        run.setRollingSteps(40);
        run.setStatus("success");

        when(predictionMapper.selectBatchById(1L)).thenReturn(batch);
        when(predictionMapper.selectModels(any(PredictionQuery.class), anyInt())).thenReturn(Collections.singletonList(model));
        when(predictionMapper.selectRunsByBatch(1L)).thenReturn(Collections.singletonList(run));
    }

    @Test
    public void rejectsAContractFeatureMissingFromResults() {
        PredictionFeatureMapping missingFeature = feature("point1_1.8YD_value");
        batch.setFeatureCount(2);
        when(predictionMapper.selectFeatures(any(PredictionQuery.class), anyInt()))
                .thenReturn(asList(feature, missingFeature));
        when(predictionMapper.selectSeries(any(PredictionQuery.class), anyInt()))
                .thenReturn(series(feature.getFeatureCode()));

        PredictionExecutionGate gate = service.evaluate(1L, PredictionExecutionMode.REPLAY, batch.getBaseTime());

        assertFalse(gate.getFeatureSetValid());
        assertFalse(gate.getTimelineValid());
        assertFalse(gate.getExecutionEligible());
        assertTrue(gate.getMissingFeatures().stream().anyMatch(value -> value.contains(missingFeature.getFeatureCode())));
    }

    @Test
    public void replayUsesScenarioTimeWhileOperationalUsesWallClockPolicy() {
        when(predictionMapper.selectFeatures(any(PredictionQuery.class), anyInt()))
                .thenReturn(Collections.singletonList(feature));
        when(predictionMapper.selectSeries(any(PredictionQuery.class), anyInt()))
                .thenReturn(series(feature.getFeatureCode()));

        PredictionExecutionGate replay = service.evaluate(1L, PredictionExecutionMode.REPLAY, batch.getBaseTime().plusMinutes(120));
        PredictionExecutionGate operational = service.evaluate(1L, PredictionExecutionMode.OPERATIONAL, batch.getBaseTime().plusMinutes(20));

        assertTrue(replay.getFreshnessValid());
        assertTrue(replay.getResultIntegrityValid());
        assertTrue(replay.getExecutionEligible());
        assertFalse(operational.getFreshnessValid());
        assertFalse(operational.getExecutionEligible());
    }

    @Test
    public void rejectsLegacyBatchWithoutPersistedIntegrityHash() {
        List<PredictionDisplay> rows = stubValidSeries();
        run.setPersistedResultHash(null);

        PredictionExecutionGate gate = service.inspect(1L, PredictionExecutionMode.REPLAY, batch.getBaseTime());

        assertFalse(gate.getResultIntegrityValid());
        assertFalse(gate.getExecutionEligible());
    }

    @Test
    public void rejectsUnsupportedIntegrityHashVersion() {
        stubValidSeries();
        run.setPersistedResultHashVersion("unsupported-v0");

        PredictionExecutionGate gate = service.inspect(1L, PredictionExecutionMode.REPLAY, batch.getBaseTime());

        assertFalse(gate.getResultIntegrityValid());
        assertFalse(gate.getExecutionEligible());
    }

    @Test
    public void rejectsPersistedPredictionValueMutation() {
        List<PredictionDisplay> rows = stubValidSeries();
        rows.get(0).setStoredPredictedValue(BigDecimal.valueOf(999));

        PredictionExecutionGate gate = service.inspect(1L, PredictionExecutionMode.REPLAY, batch.getBaseTime());

        assertFalse(gate.getResultIntegrityValid());
        assertFalse(gate.getExecutionEligible());
    }

    @Test
    public void rejectsEngineeringValueMutation() {
        List<PredictionDisplay> rows = stubValidSeries();
        rows.get(0).setEngineeringValue(BigDecimal.valueOf(999));

        assertFalse(service.inspect(1L, PredictionExecutionMode.REPLAY, batch.getBaseTime()).getResultIntegrityValid());
    }

    @Test
    public void rejectsUnitMutationWithStaleHash() {
        List<PredictionDisplay> rows = stubValidSeries();
        rows.get(0).setEngineeringUnit("kPa");

        assertFalse(service.inspect(1L, PredictionExecutionMode.REPLAY, batch.getBaseTime()).getResultIntegrityValid());
    }

    @Test
    public void acceptsRecomputedIntegrityBeforeSemanticUnitValidation() {
        List<PredictionDisplay> rows = stubValidSeries();
        rows.forEach(row -> row.setEngineeringUnit("kPa"));
        String recomputed = integrityHashService.resultHash(rows);
        run.setPersistedResultHash(recomputed);
        batch.setPersistedOutputHash(integrityHashService.outputHash(Collections.singletonMap("YD@v1", recomputed)));

        PredictionExecutionGate gate = service.inspect(1L, PredictionExecutionMode.REPLAY, batch.getBaseTime());

        assertTrue(gate.getResultIntegrityValid());
        assertTrue(gate.getExecutionEligible());
    }

    @Test
    public void rejectsBatchAggregateMismatch() {
        stubValidSeries();
        batch.setPersistedOutputHash("0f0f0f0f");

        PredictionExecutionGate gate = service.inspect(1L, PredictionExecutionMode.REPLAY, batch.getBaseTime());

        assertFalse(gate.getResultIntegrityValid());
        assertFalse(gate.getExecutionEligible());
    }

    @Test
    public void rechecksRowsAfterAValidEvaluation() {
        List<PredictionDisplay> rows = stubValidSeries();
        assertTrue(service.inspect(1L, PredictionExecutionMode.REPLAY, batch.getBaseTime()).getExecutionEligible());

        rows.get(0).setEngineeringValue(BigDecimal.valueOf(1000));
        PredictionExecutionGate rechecked = service.inspect(1L, PredictionExecutionMode.REPLAY, batch.getBaseTime());

        assertFalse(rechecked.getResultIntegrityValid());
        assertFalse(rechecked.getExecutionEligible());
    }

    private List<PredictionDisplay> stubValidSeries() {
        when(predictionMapper.selectFeatures(any(PredictionQuery.class), anyInt()))
                .thenReturn(Collections.singletonList(feature));
        List<PredictionDisplay> rows = series(feature.getFeatureCode());
        when(predictionMapper.selectSeries(any(PredictionQuery.class), anyInt())).thenReturn(rows);
        return rows;
    }

    private PredictionFeatureMapping feature(String code) {
        PredictionFeatureMapping result = new PredictionFeatureMapping();
        result.setModelId(10L);
        result.setTargetType("YD");
        result.setFeatureCode(code);
        result.setFeatureRole("model_input");
        result.setRequired(1);
        result.setPredictionTarget(1);
        result.setEnabled(1);
        return result;
    }

    private List<PredictionDisplay> series(String featureCode) {
        List<PredictionDisplay> rows = new ArrayList<PredictionDisplay>();
        for (int step = 1; step <= 40; step++) {
            PredictionDisplay row = new PredictionDisplay();
            row.setModelCode("YD");
            row.setModelVersion("v1");
            row.setProjectId(1L);
            row.setRunId(20L);
            row.setTargetType("YD");
            row.setFeatureCode(featureCode);
            row.setMetricCode("displacement_tilt_y_deg");
            row.setEngineeringMetricCode("deep_horizontal_displacement_y");
            row.setStep(step);
            row.setHorizonMinutes(step * 3);
            row.setBaseTime(batch.getBaseTime());
            row.setFutureTime(batch.getBaseTime().plusMinutes(step * 3L));
            row.setPersistedBaseTime(batch.getBaseTime());
            row.setPersistedFutureTime(batch.getBaseTime().plusMinutes(step * 3L));
            row.setRawPredictedValue(BigDecimal.valueOf(step));
            row.setRawPredictedUnit("deg");
            row.setStoredPredictedValue(BigDecimal.valueOf(step));
            row.setStoredPredictedUnit("deg");
            row.setEngineeringValue(BigDecimal.valueOf(step));
            row.setEngineeringUnit("mm");
            row.setConversionOperatorCode("displacement_y_engineering");
            row.setConversionVersion("displacement-v2-20260714");
            row.setConversionStatus("success");
            row.setQualityFlag("normal");
            row.setSourceRecordKey("BATCH-1:YD:" + featureCode + ":" + step);
            rows.add(row);
        }
        String hash = integrityHashService.resultHash(rows);
        run.setPersistedResultHash(hash);
        batch.setPersistedOutputHashVersion(PersistedPredictionIntegrityHashService.OUTPUT_HASH_VERSION);
        batch.setPersistedOutputHash(integrityHashService.outputHash(Collections.singletonMap("YD@v1", hash)));
        return rows;
    }

    private <T> List<T> asList(T first, T second) {
        List<T> rows = new ArrayList<T>();
        rows.add(first);
        rows.add(second);
        return rows;
    }
}
