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

    @BeforeEach
    public void setUp() {
        predictionMapper = mock(PredictionMapper.class);
        PredictionExecutionGateMapper gateMapper = mock(PredictionExecutionGateMapper.class);
        ObjectMapper objectMapper = new ObjectMapper();
        service = new PredictionExecutionGateServiceImpl(
                predictionMapper,
                gateMapper,
                new CanonicalHashService(objectMapper),
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
        assertTrue(replay.getExecutionEligible());
        assertFalse(operational.getFreshnessValid());
        assertFalse(operational.getExecutionEligible());
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
            row.setTargetType("YD");
            row.setFeatureCode(featureCode);
            row.setStep(step);
            row.setHorizonMinutes(step * 3);
            row.setBaseTime(batch.getBaseTime());
            row.setFutureTime(batch.getBaseTime().plusMinutes(step * 3L));
            row.setQualityFlag("normal");
            rows.add(row);
        }
        return rows;
    }

    private <T> List<T> asList(T first, T second) {
        List<T> rows = new ArrayList<T>();
        rows.add(first);
        rows.add(second);
        return rows;
    }
}
