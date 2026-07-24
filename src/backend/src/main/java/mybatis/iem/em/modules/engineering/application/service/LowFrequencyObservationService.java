package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.domain.model.LowFrequencyObservation;
import mybatis.iem.em.modules.engineering.application.dto.ObservationQuery;

import java.util.List;

public interface LowFrequencyObservationService {
    List<LowFrequencyObservation> list(ObservationQuery query);
}





