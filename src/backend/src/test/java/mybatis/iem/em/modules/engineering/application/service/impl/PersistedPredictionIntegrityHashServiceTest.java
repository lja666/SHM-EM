package mybatis.iem.em.modules.engineering.application.service.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import mybatis.iem.em.modules.engineering.domain.model.PredictionDisplay;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;

public class PersistedPredictionIntegrityHashServiceTest {
    @Test
    public void matchesTheSharedPythonFixture() throws Exception {
        ObjectMapper objectMapper = new ObjectMapper();
        Path fixturePath = Paths.get("..", "pit_pre", "tests", "fixtures", "persisted-integrity-fixture.json")
                .toAbsolutePath().normalize();
        Map<String, Object> fixture = objectMapper.readValue(
                Files.readAllBytes(fixturePath),
                new TypeReference<Map<String, Object>>() {});
        PersistedPredictionIntegrityHashService service = new PersistedPredictionIntegrityHashService(objectMapper);
        List<PredictionDisplay> rows = rows(fixture);

        String resultHash = service.resultHash(rows);
        assertEquals(fixture.get("expectedResultHash"), resultHash);
        assertEquals(
                fixture.get("expectedOutputHash"),
                service.outputHash(Collections.singletonMap(String.valueOf(fixture.get("modelKey")), resultHash)));
        assertEquals(PersistedPredictionIntegrityHashService.RESULT_HASH_VERSION, fixture.get("resultHashVersion"));
        assertEquals(PersistedPredictionIntegrityHashService.OUTPUT_HASH_VERSION, fixture.get("outputHashVersion"));

        rows.get(0).setEngineeringValue(rows.get(0).getEngineeringValue().add(BigDecimal.ONE));
        assertNotEquals(resultHash, service.resultHash(rows));
    }

    @SuppressWarnings("unchecked")
    private List<PredictionDisplay> rows(Map<String, Object> fixture) {
        List<PredictionDisplay> result = new ArrayList<PredictionDisplay>();
        for (Map<String, Object> source : (List<Map<String, Object>>) fixture.get("rows")) {
            PredictionDisplay row = new PredictionDisplay();
            row.setTargetType(text(source, "target_type"));
            row.setFeatureCode(text(source, "feature_code"));
            row.setProjectId(longValue(source, "project_id"));
            row.setStationId(longValue(source, "station_id"));
            row.setInstrumentId(longValue(source, "instrument_id"));
            row.setMetricCode(text(source, "metric_code"));
            row.setEngineeringMetricCode(text(source, "engineering_metric_code"));
            row.setStep(integer(source, "step"));
            row.setHorizonMinutes(integer(source, "horizon_minutes"));
            row.setPersistedBaseTime(datetime(source, "base_time"));
            row.setPersistedFutureTime(datetime(source, "future_time"));
            row.setRawPredictedValue(decimal(source, "raw_predicted_value"));
            row.setRawPredictedUnit(text(source, "raw_predicted_unit"));
            row.setStoredPredictedValue(decimal(source, "predicted_value"));
            row.setStoredPredictedUnit(text(source, "predicted_unit"));
            row.setEngineeringValue(decimal(source, "engineering_value"));
            row.setEngineeringUnit(text(source, "engineering_unit"));
            row.setRawLowerBound(decimal(source, "lower_bound"));
            row.setRawUpperBound(decimal(source, "upper_bound"));
            row.setEngineeringLowerBound(decimal(source, "engineering_lower_bound"));
            row.setEngineeringUpperBound(decimal(source, "engineering_upper_bound"));
            row.setConfidence(decimal(source, "confidence"));
            row.setConversionOperatorCode(text(source, "conversion_operator_code"));
            row.setConversionVersion(text(source, "conversion_version"));
            row.setConversionStatus(text(source, "conversion_status"));
            row.setQualityFlag(text(source, "quality_flag"));
            row.setSourceRecordKey(text(source, "source_record_key"));
            result.add(row);
        }
        return result;
    }

    private String text(Map<String, Object> source, String key) {
        Object value = source.get(key);
        return value == null ? null : String.valueOf(value);
    }

    private BigDecimal decimal(Map<String, Object> source, String key) {
        String value = text(source, key);
        return value == null ? null : new BigDecimal(value);
    }

    private LocalDateTime datetime(Map<String, Object> source, String key) {
        String value = text(source, key);
        return value == null ? null : LocalDateTime.parse(value);
    }

    private Long longValue(Map<String, Object> source, String key) {
        Object value = source.get(key);
        return value == null ? null : ((Number) value).longValue();
    }

    private Integer integer(Map<String, Object> source, String key) {
        Object value = source.get(key);
        return value == null ? null : ((Number) value).intValue();
    }
}
