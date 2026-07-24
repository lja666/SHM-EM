package mybatis.iem.em.modules.engineering.domain.model;

public enum PredictionExecutionMode {
    OPERATIONAL,
    REPLAY,
    REPRODUCTION;

    public static PredictionExecutionMode from(String value, PredictionExecutionMode fallback) {
        if (value == null || value.trim().isEmpty()) {
            return fallback;
        }
        try {
            return valueOf(value.trim().toUpperCase());
        } catch (IllegalArgumentException ex) {
            throw new IllegalArgumentException("Unsupported prediction execution mode: " + value, ex);
        }
    }
}
