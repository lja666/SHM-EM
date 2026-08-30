package mybatis.iem.em.modules.engineering.application.service.impl;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import mybatis.iem.em.modules.engineering.domain.model.PredictionDisplay;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

@Component
public class PersistedPredictionIntegrityHashService {
    public static final String RESULT_HASH_VERSION = "prediction-persisted-integrity-v1";
    public static final String OUTPUT_HASH_VERSION = "prediction-persisted-output-integrity-v1";
    private static final DateTimeFormatter DATETIME_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS");

    private final ObjectMapper objectMapper;

    public PersistedPredictionIntegrityHashService(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public String resultHash(List<PredictionDisplay> source) {
        List<PredictionDisplay> rows = new ArrayList<PredictionDisplay>(source);
        rows.sort(Comparator
                .comparing(PredictionDisplay::getFeatureCode, Comparator.nullsFirst(String::compareTo))
                .thenComparing(PredictionDisplay::getStep, Comparator.nullsFirst(Integer::compareTo))
                .thenComparing(PredictionDisplay::getSourceRecordKey, Comparator.nullsFirst(String::compareTo)));
        List<String> lines = new ArrayList<String>();
        lines.add(RESULT_HASH_VERSION);
        for (PredictionDisplay row : rows) {
            List<String> values = new ArrayList<String>();
            values.add(row.getTargetType());
            values.add(row.getFeatureCode());
            values.add(integer(row.getProjectId()));
            values.add(integer(row.getStationId()));
            values.add(integer(row.getInstrumentId()));
            values.add(row.getMetricCode());
            values.add(row.getEngineeringMetricCode());
            values.add(integer(row.getStep()));
            values.add(integer(row.getHorizonMinutes()));
            values.add(datetime(row.getPersistedBaseTime()));
            values.add(datetime(row.getPersistedFutureTime()));
            values.add(decimal(row.getRawPredictedValue(), 8));
            values.add(row.getRawPredictedUnit());
            values.add(decimal(row.getStoredPredictedValue(), 8));
            values.add(row.getStoredPredictedUnit());
            values.add(decimal(row.getEngineeringValue(), 8));
            values.add(row.getEngineeringUnit());
            values.add(decimal(row.getRawLowerBound(), 8));
            values.add(decimal(row.getRawUpperBound(), 8));
            values.add(decimal(row.getEngineeringLowerBound(), 8));
            values.add(decimal(row.getEngineeringUpperBound(), 8));
            values.add(decimal(row.getConfidence(), 6));
            values.add(row.getConversionOperatorCode());
            values.add(row.getConversionVersion());
            values.add(row.getConversionStatus());
            values.add(row.getQualityFlag());
            values.add(row.getSourceRecordKey());
            lines.add(json(values));
        }
        return sha256(String.join("\n", lines));
    }

    public String outputHash(Map<String, String> source) {
        Map<String, String> sorted = new TreeMap<String, String>(source);
        List<String> lines = new ArrayList<String>();
        lines.add(OUTPUT_HASH_VERSION);
        for (Map.Entry<String, String> entry : sorted.entrySet()) {
            List<String> values = new ArrayList<String>();
            values.add(entry.getKey());
            values.add(entry.getValue());
            lines.add(json(values));
        }
        return sha256(String.join("\n", lines));
    }

    private String json(List<String> values) {
        try {
            return objectMapper.writeValueAsString(values);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Failed to serialize persisted prediction integrity payload", ex);
        }
    }

    private String integer(Number value) {
        return value == null ? null : String.valueOf(value.longValue());
    }

    private String decimal(BigDecimal value, int scale) {
        return value == null ? null : value.setScale(scale, RoundingMode.HALF_UP).toPlainString();
    }

    private String datetime(LocalDateTime value) {
        return value == null ? null : value.format(DATETIME_FORMAT);
    }

    private String sha256(String payload) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(payload.getBytes(StandardCharsets.UTF_8));
            StringBuilder result = new StringBuilder(digest.length * 2);
            for (byte value : digest) result.append(String.format("%02x", value & 0xff));
            return result.toString();
        } catch (Exception ex) {
            throw new IllegalStateException("Failed to hash persisted prediction integrity payload", ex);
        }
    }
}
