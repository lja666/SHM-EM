package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.common.BusinessException;
import mybatis.iem.em.modules.engineering.application.dto.ObservationQuery;
import mybatis.iem.em.modules.engineering.domain.model.ObservationTableRegistry;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.ObservationTableRegistryMapper;
import mybatis.iem.em.modules.engineering.application.service.ObservationRoutingService;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.regex.Pattern;

@Service
public class ObservationRoutingServiceImpl implements ObservationRoutingService {
    private static final Pattern SAFE_TABLE_NAME = Pattern.compile("^em_[a-z0-9_]+$");
    private final ObservationTableRegistryMapper registryMapper;

    public ObservationRoutingServiceImpl(ObservationTableRegistryMapper registryMapper) {
        this.registryMapper = registryMapper;
    }

    @Override
    public ObservationTableRegistry requireQueryableRegistry(String registryCode, String expectedStorageMode) {
        if (!StringUtils.hasText(registryCode)) {
            throw new BusinessException("registryCode is required");
        }
        ObservationTableRegistry registry = registryMapper.selectByCode(registryCode);
        return validateRegistry(registry, registryCode, expectedStorageMode);
    }

    @Override
    public ObservationTableRegistry requireQueryableRegistry(ObservationQuery query, String expectedStorageMode) {
        if (StringUtils.hasText(query.getRegistryCode())) {
            return requireQueryableRegistry(query.getRegistryCode(), expectedStorageMode);
        }
        ObservationTableRegistry registry = registryMapper.selectBestMatch(
                query.getProjectId(),
                query.getInstrumentId(),
                query.getInstrumentType(),
                query.getMetricCode(),
                expectedStorageMode
        );
        return validateRegistry(registry, "auto-resolved", expectedStorageMode);
    }

    private ObservationTableRegistry validateRegistry(ObservationTableRegistry registry, String registryCode, String expectedStorageMode) {
        if (registry == null) {
            throw new BusinessException("observation registry is not found: " + registryCode);
        }
        if (registry.getEnabled() == null || registry.getEnabled() != 1) {
            throw new BusinessException("observation registry is not enabled: " + registryCode);
        }
        if (registry.getIsQueryable() == null || registry.getIsQueryable() != 1) {
            throw new BusinessException("observation registry is not queryable: " + registryCode);
        }
        if (StringUtils.hasText(expectedStorageMode) && !expectedStorageMode.equals(registry.getStorageMode())) {
            throw new BusinessException("registry storage mode mismatch: " + registryCode);
        }
        if (!StringUtils.hasText(registry.getPhysicalTableName()) || !SAFE_TABLE_NAME.matcher(registry.getPhysicalTableName()).matches()) {
            throw new BusinessException("unsafe observation table registered: " + registryCode);
        }
        return registry;
    }
}





