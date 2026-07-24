package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.domain.model.AccelerationWaveform;
import mybatis.iem.em.modules.engineering.application.dto.ObservationQuery;

import java.util.List;

public interface AccelerationWaveformService {
    List<AccelerationWaveform> list(ObservationQuery query);
}





