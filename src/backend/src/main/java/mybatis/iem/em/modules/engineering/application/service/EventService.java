package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.domain.model.Event;
import mybatis.iem.em.modules.engineering.application.dto.EventActionRequest;

import java.util.List;
import java.util.Map;

public interface EventService {
    List<Event> list(Long projectId, Integer limit);

    List<Map<String, Object>> deviceWarnings(Long projectId, Integer limit);

    Event get(Long id);

    Event acknowledge(Long id, EventActionRequest request, String ipAddress);

    Event assign(Long id, EventActionRequest request, String ipAddress);

    Event changeLevel(Long id, EventActionRequest request, String ipAddress);

    Event resolve(Long id, EventActionRequest request, String ipAddress);

    Event close(Long id, EventActionRequest request, String ipAddress);
}





