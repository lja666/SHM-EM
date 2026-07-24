package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class EngineeringConversionResult {
    private BigDecimal rawValue;
    private String rawUnit;
    private BigDecimal engineeringValue;
    private String engineeringUnit;
    private String engineeringMetricCode;
    private String operatorCode;
    private String conversionVersion;
    private String status;
    private String remark;

    public boolean isSuccessful() {
        return "success".equalsIgnoreCase(status) && engineeringValue != null;
    }
}
