package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.domain.model.EngineeringConversionResult;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class EngineeringConversionServiceImplTest {
    private final EngineeringConversionServiceImpl service = new EngineeringConversionServiceImpl();

    @Test
    void convertsDisplacementYWithCalibratedInitialValue() {
        Map<String, BigDecimal> parameters = values("initial_y_mm", "2.92");
        EngineeringConversionResult result = service.convert("displacement_y_engineering",
                bd("1.48"), "degree", bd("1.49"), null, null, parameters);
        BigDecimal expected = BigDecimal.valueOf(1000 * (Math.sin(Math.toRadians(1.48)) - Math.sin(Math.toRadians(1.49))) + 2.92)
                .setScale(8, java.math.RoundingMode.HALF_UP);
        assertEquals(expected, result.getEngineeringValue());
        assertEquals("mm", result.getEngineeringUnit());
    }

    @Test
    void convertsDisplacementXWithZeroInitialValue() {
        EngineeringConversionResult result = service.convert("displacement_x_engineering",
                bd("2.31"), "degree", bd("2.29"), null, null, null);
        BigDecimal expected = BigDecimal.valueOf(1000 * (Math.sin(Math.toRadians(2.31)) - Math.sin(Math.toRadians(2.29))))
                .setScale(8, java.math.RoundingMode.HALF_UP);
        assertEquals(expected, result.getEngineeringValue());
    }

    @Test
    void compensatesStaticLevelAgainstReferencePoint() {
        EngineeringConversionResult result = service.convert("static_level_reference_compensation",
                bd("54.13"), "mm", bd("46.00"), bd("35.87"), bd("37.15"), null);
        assertEquals(bd("9.41000000"), result.getEngineeringValue());
    }

    @Test
    void separatesPitElevationAndCumulativeChange() {
        EngineeringConversionResult elevation = service.convert("pit_water_elevation",
                bd("2727"), "mm", null, null, null, values("module_elevation_m", "11"));
        EngineeringConversionResult change = service.convert("pit_water_cumulative_change",
                bd("2727"), "mm", null, null, null, values("cumulative_baseline_m", "2.731"));
        assertEquals(bd("8.27300000"), elevation.getEngineeringValue());
        assertEquals(bd("-0.00400000"), change.getEngineeringValue());
    }

    @Test
    void appliesLaboratoryInitialErrorAndInstallationOffset() {
        Map<String, BigDecimal> parameters = values("initial_error_cm", "1.5");
        parameters.put("installation_offset_cm", bd("5"));
        EngineeringConversionResult result = service.convert("laboratory_water_level",
                bd("75"), "mm", null, null, null, parameters);
        assertEquals(bd("11.00000000"), result.getEngineeringValue());
    }

    @Test
    void neverFallsBackToRawWhenPrerequisiteIsMissing() {
        EngineeringConversionResult result = service.convert("displacement_y_engineering",
                bd("1.48"), "degree", null, null, null, values("initial_y_mm", "2.92"));
        assertEquals("missing_prerequisite", result.getStatus());
        assertNull(result.getEngineeringValue());
    }

    private Map<String, BigDecimal> values(String key, String value) {
        Map<String, BigDecimal> result = new HashMap<String, BigDecimal>();
        result.put(key, bd(value));
        return result;
    }

    private BigDecimal bd(String value) {
        return new BigDecimal(value);
    }
}
