package mybatis.iem.em;

import mybatis.iem.em.common.BusinessException;
import mybatis.iem.em.modules.engineering.application.service.impl.ObservationRoutingServiceImpl;
import mybatis.iem.em.modules.engineering.domain.model.ObservationTableRegistry;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.ObservationTableRegistryMapper;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

public class ObservationRoutingServiceImplTest {
    @Test
    public void rejectsUnsafeRegisteredTableName() {
        ObservationTableRegistryMapper mapper = mock(ObservationTableRegistryMapper.class);
        ObservationTableRegistry registry = new ObservationTableRegistry();
        registry.setRegistryCode("BAD_TABLE");
        registry.setEnabled(1);
        registry.setIsQueryable(1);
        registry.setStorageMode("type_table");
        registry.setPhysicalTableName("em_obs_unknown;drop table em_project");
        when(mapper.selectByCode("BAD_TABLE")).thenReturn(registry);

        ObservationRoutingServiceImpl service = new ObservationRoutingServiceImpl(mapper);

        assertThrows(BusinessException.class, () -> service.requireQueryableRegistry("BAD_TABLE", "type_table"));
    }

    @Test
    public void acceptsTypedObservationTable() {
        ObservationTableRegistry registry = registry("LOW_DISPLACEMENT", "type_table", "em_obs_displacement");
        ObservationTableRegistryMapper mapper = mock(ObservationTableRegistryMapper.class);
        when(mapper.selectByCode("LOW_DISPLACEMENT")).thenReturn(registry);

        ObservationRoutingServiceImpl service = new ObservationRoutingServiceImpl(mapper);

        assertSame(registry, service.requireQueryableRegistry("LOW_DISPLACEMENT", "type_table"));
    }

    @Test
    public void acceptsAccelerationSensorPartition() {
        ObservationTableRegistry registry = registry("ACC_1426000125", "sensor_table", "em_accel_s_1426000125");
        ObservationTableRegistryMapper mapper = mock(ObservationTableRegistryMapper.class);
        when(mapper.selectByCode("ACC_1426000125")).thenReturn(registry);

        ObservationRoutingServiceImpl service = new ObservationRoutingServiceImpl(mapper);

        assertSame(registry, service.requireQueryableRegistry("ACC_1426000125", "sensor_table"));
    }

    private ObservationTableRegistry registry(String code, String storageMode, String tableName) {
        ObservationTableRegistry registry = new ObservationTableRegistry();
        registry.setRegistryCode(code);
        registry.setEnabled(1);
        registry.setIsQueryable(1);
        registry.setStorageMode(storageMode);
        registry.setPhysicalTableName(tableName);
        return registry;
    }
}
