package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.application.service.EngineeringConversionService;
import mybatis.iem.em.modules.engineering.domain.model.EngineeringConversionResult;
import mybatis.iem.em.modules.engineering.domain.model.LowFrequencyObservation;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Collections;
import java.util.Map;

@Service
public class EngineeringConversionServiceImpl implements EngineeringConversionService {
    private static final BigDecimal THOUSAND = BigDecimal.valueOf(1000);
    private static final BigDecimal TEN = BigDecimal.TEN;

    @Override
    public EngineeringConversionResult convert(String operatorCode,
                                                BigDecimal rawValue,
                                                String rawUnit,
                                                BigDecimal baselineValue,
                                                BigDecimal referenceRawValue,
                                                BigDecimal referenceBaselineValue,
                                                Map<String, BigDecimal> parameters) {
        Map<String, BigDecimal> values = parameters == null ? Collections.<String, BigDecimal>emptyMap() : parameters;
        EngineeringConversionResult result = base(operatorCode, rawValue, rawUnit);
        if (rawValue == null) return missing(result, "Raw value is missing");
        if ("identity".equals(operatorCode)) {
            result.setEngineeringValue(rawValue);
            result.setEngineeringUnit(rawUnit);
            result.setEngineeringMetricCode(null);
            return success(result, "Identity engineering mapping");
        }
        if ("displacement_y_engineering".equals(operatorCode)) {
            BigDecimal initialY = values.get("initial_y_mm");
            if (baselineValue == null || initialY == null) return missing(result, "Baseline angle or initial Y is missing");
            result.setEngineeringValue(angleDelta(rawValue, baselineValue).add(initialY).setScale(8, RoundingMode.HALF_UP));
            result.setEngineeringUnit("mm");
            result.setEngineeringMetricCode("deep_horizontal_displacement_y");
            return success(result, "Y angle converted with baseline angle and calibrated initial Y");
        }
        if ("displacement_x_engineering".equals(operatorCode)) {
            if (baselineValue == null) return missing(result, "Baseline angle is missing");
            result.setEngineeringValue(angleDelta(rawValue, baselineValue).setScale(8, RoundingMode.HALF_UP));
            result.setEngineeringUnit("mm");
            result.setEngineeringMetricCode("deep_horizontal_displacement_x");
            return success(result, "X angle converted with baseline angle; initial X is zero");
        }
        if ("static_level_reference_compensation".equals(operatorCode)) {
            if (baselineValue == null || referenceRawValue == null || referenceBaselineValue == null) {
                return missing(result, "Point baseline or matching reference reading is missing");
            }
            result.setEngineeringValue(rawValue.subtract(baselineValue)
                    .subtract(referenceRawValue.subtract(referenceBaselineValue)).setScale(8, RoundingMode.HALF_UP));
            result.setEngineeringUnit("mm");
            result.setEngineeringMetricCode("ground_settlement");
            return success(result, "Point change minus reference-point change");
        }
        if ("pit_water_elevation".equals(operatorCode)) {
            BigDecimal elevation = values.get("module_elevation_m");
            if (elevation == null) return missing(result, "Module elevation is missing");
            result.setEngineeringValue(elevation.subtract(rawValue.divide(THOUSAND, 8, RoundingMode.HALF_UP)));
            result.setEngineeringUnit("m");
            result.setEngineeringMetricCode("groundwater_elevation_m");
            return success(result, "Module elevation minus pressure head");
        }
        if ("pit_water_cumulative_change".equals(operatorCode)) {
            BigDecimal baseline = values.get("cumulative_baseline_m");
            if (baseline == null) return missing(result, "Cumulative water-level baseline is missing");
            result.setEngineeringValue(rawValue.divide(THOUSAND, 8, RoundingMode.HALF_UP).subtract(baseline));
            result.setEngineeringUnit("m");
            result.setEngineeringMetricCode("groundwater_level_change");
            return success(result, "Cumulative water-level change; distinct from elevation");
        }
        if ("laboratory_water_level".equals(operatorCode)) {
            BigDecimal initialError = values.get("initial_error_cm");
            BigDecimal offset = values.get("installation_offset_cm");
            if (initialError == null || offset == null) return missing(result, "Laboratory initial error or installation offset is missing");
            result.setEngineeringValue(rawValue.divide(TEN, 8, RoundingMode.HALF_UP).subtract(initialError).add(offset));
            result.setEngineeringUnit("cm");
            result.setEngineeringMetricCode("special_differential_water_level_cm");
            return success(result, "Laboratory water level corrected by initial error and installation offset");
        }
        return missing(result, "Unknown engineering conversion operator: " + operatorCode);
    }

    @Override
    public void decorateStoredObservation(LowFrequencyObservation observation) {
        observation.setEngineeringValue(observation.getMetricValue());
        observation.setEngineeringUnit(observation.getMetricUnit());
        if (observation.getConversionStatus() == null) {
            observation.setConversionStatus(observation.getMetricValue() == null ? "missing_prerequisite" : "success");
        }
    }

    private BigDecimal angleDelta(BigDecimal raw, BigDecimal baseline) {
        double value = THOUSAND.doubleValue()
                * (Math.sin(Math.toRadians(raw.doubleValue())) - Math.sin(Math.toRadians(baseline.doubleValue())));
        return BigDecimal.valueOf(value);
    }

    private EngineeringConversionResult base(String operatorCode, BigDecimal rawValue, String rawUnit) {
        EngineeringConversionResult result = new EngineeringConversionResult();
        result.setOperatorCode(operatorCode);
        result.setRawValue(rawValue);
        result.setRawUnit(rawUnit);
        return result;
    }

    private EngineeringConversionResult success(EngineeringConversionResult result, String remark) {
        result.setStatus("success");
        result.setRemark(remark);
        return result;
    }

    private EngineeringConversionResult missing(EngineeringConversionResult result, String remark) {
        result.setStatus("missing_prerequisite");
        result.setRemark(remark);
        return result;
    }
}
