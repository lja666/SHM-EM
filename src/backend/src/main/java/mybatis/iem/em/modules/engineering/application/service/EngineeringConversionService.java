package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.domain.model.EngineeringConversionResult;
import mybatis.iem.em.modules.engineering.domain.model.LowFrequencyObservation;

import java.math.BigDecimal;
import java.util.Map;

public interface EngineeringConversionService {
    EngineeringConversionResult convert(String operatorCode,
                                         BigDecimal rawValue,
                                         String rawUnit,
                                         BigDecimal baselineValue,
                                         BigDecimal referenceRawValue,
                                         BigDecimal referenceBaselineValue,
                                         Map<String, BigDecimal> parameters);

    void decorateStoredObservation(LowFrequencyObservation observation);
}
