package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

public interface EventResponseWorkflowMapper {
    List<Map<String, Object>> selectNotificationChannels(@Param("projectId") Long projectId);

    List<Map<String, Object>> selectResponseWorkflows(@Param("projectId") Long projectId);

    Map<String, Object> selectResponseWorkflowByEvent(@Param("projectId") Long projectId,
                                                      @Param("eventId") Long eventId);

    List<Map<String, Object>> selectResponseSteps(@Param("workflowId") Long workflowId);

    List<Map<String, Object>> selectReportInstancesByEvent(@Param("projectId") Long projectId,
                                                           @Param("eventId") Long eventId);

    List<Map<String, Object>> selectEvidenceResourcesByEvent(@Param("projectId") Long projectId,
                                                             @Param("eventId") Long eventId);

    List<Map<String, Object>> selectActionLogsByEvent(@Param("projectId") Long projectId,
                                                      @Param("eventId") Long eventId);

    int insertWorkflow(@Param("eventId") Long eventId, @Param("projectId") Long projectId);

    Long selectWorkflowId(@Param("eventId") Long eventId);

    int insertStep(@Param("workflowId") Long workflowId,
                   @Param("stepOrder") Integer stepOrder,
                   @Param("stepCode") String stepCode,
                   @Param("stepName") String stepName,
                   @Param("status") String status,
                   @Param("relatedTaskType") String relatedTaskType,
                   @Param("relatedTaskId") Long relatedTaskId);

    int insertReportInstance(@Param("eventId") Long eventId, @Param("projectId") Long projectId);

    Long selectReportInstanceId(@Param("eventId") Long eventId, @Param("projectId") Long projectId);

    int completeWorkflow(@Param("workflowId") Long workflowId,
                         @Param("notificationTaskId") Long notificationTaskId,
                         @Param("reportId") Long reportId);
}
