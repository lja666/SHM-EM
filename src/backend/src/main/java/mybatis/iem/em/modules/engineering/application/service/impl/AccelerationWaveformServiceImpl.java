package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.domain.model.AccelerationWaveform;
import mybatis.iem.em.modules.engineering.domain.model.ObservationTableRegistry;
import mybatis.iem.em.modules.engineering.application.dto.ObservationQuery;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.AccelerationWaveformMapper;
import mybatis.iem.em.modules.engineering.application.service.AccelerationWaveformService;
import mybatis.iem.em.modules.engineering.application.service.ObservationRoutingService;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class AccelerationWaveformServiceImpl implements AccelerationWaveformService {
    private final ObservationRoutingService routingService;
    private final AccelerationWaveformMapper mapper;

    public AccelerationWaveformServiceImpl(ObservationRoutingService routingService, AccelerationWaveformMapper mapper) {
        this.routingService = routingService;
        this.mapper = mapper;
    }

    @Override
    public List<AccelerationWaveform> list(ObservationQuery query) {
        ObservationTableRegistry registry = routingService.requireQueryableRegistry(query, "sensor_table");
        return mapper.selectByRegistry(registry.getPhysicalTableName(), query, normalizeLimit(query.getLimit()));
    }

    private Integer normalizeLimit(Integer limit) {
        if (limit == null || limit <= 0) {
            return 1000;
        }
        return Math.min(limit, 10000);
    }
}





