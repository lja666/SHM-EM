package mybatis.iem.em;

import mybatis.iem.em.modules.engineering.api.controller.AccelerationWaveformController;
import mybatis.iem.em.modules.engineering.api.controller.ProjectRuleController;
import mybatis.iem.em.modules.engineering.api.controller.LowFrequencyObservationController;
import mybatis.iem.em.modules.engineering.api.controller.PredictionController;
import mybatis.iem.em.modules.engineering.api.controller.ProjectController;
import mybatis.iem.em.modules.engineering.domain.model.AccelerationWaveform;
import mybatis.iem.em.modules.engineering.domain.model.EventRule;
import mybatis.iem.em.modules.engineering.domain.model.LowFrequencyObservation;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionGate;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionMode;
import mybatis.iem.em.modules.engineering.domain.model.Project;
import mybatis.iem.em.modules.engineering.domain.model.ProjectFutureState;
import mybatis.iem.em.modules.engineering.application.dto.ObservationQuery;
import mybatis.iem.em.modules.engineering.application.dto.RuleEvaluationRequest;
import mybatis.iem.em.modules.engineering.application.service.AccelerationWaveformService;
import mybatis.iem.em.modules.engineering.application.service.EventEvaluationService;
import mybatis.iem.em.modules.engineering.application.service.EventRuleService;
import mybatis.iem.em.modules.engineering.application.service.LowFrequencyObservationService;
import mybatis.iem.em.modules.engineering.application.service.PredictionExecutionGateService;
import mybatis.iem.em.modules.engineering.application.service.PredictionService;
import mybatis.iem.em.modules.engineering.application.service.ProjectContextService;
import mybatis.iem.em.modules.engineering.application.service.ProjectFutureStateService;
import mybatis.iem.em.modules.engineering.application.service.ProjectService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentMatchers;
import org.springframework.validation.Errors;
import org.springframework.validation.Validator;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

public class ApiSmokeTest {
    private static final Validator NO_OP_VALIDATOR = new Validator() {
        @Override
        public boolean supports(Class<?> clazz) {
            return true;
        }

        @Override
        public void validate(Object target, Errors errors) {
            // Request validation is outside this controller-contract smoke test.
        }
    };

    private MockMvc mockMvc;

    private ProjectService projectService;
    private ProjectContextService projectContextService;
    private ProjectFutureStateService projectFutureStateService;
    private PredictionService predictionService;
    private PredictionExecutionGateService predictionExecutionGateService;
    private LowFrequencyObservationService lowFrequencyObservationService;
    private AccelerationWaveformService accelerationWaveformService;
    private EventRuleService eventRuleService;
    private EventEvaluationService eventEvaluationService;

    @BeforeEach
    public void setUp() {
        projectService = mock(ProjectService.class);
        projectContextService = mock(ProjectContextService.class);
        projectFutureStateService = mock(ProjectFutureStateService.class);
        predictionService = mock(PredictionService.class);
        predictionExecutionGateService = mock(PredictionExecutionGateService.class);
        lowFrequencyObservationService = mock(LowFrequencyObservationService.class);
        accelerationWaveformService = mock(AccelerationWaveformService.class);
        eventRuleService = mock(EventRuleService.class);
        eventEvaluationService = mock(EventEvaluationService.class);
        mockMvc = MockMvcBuilders.standaloneSetup(
                new ProjectController(projectService, projectContextService, projectFutureStateService),
                new PredictionController(predictionService, predictionExecutionGateService),
                new LowFrequencyObservationController(lowFrequencyObservationService),
                new AccelerationWaveformController(accelerationWaveformService),
                new ProjectRuleController(eventRuleService, eventEvaluationService)
        ).setValidator(NO_OP_VALIDATOR).build();
    }

    @Test
    public void projectEndpointReturnsUnifiedResponse() throws Exception {
        Project project = new Project();
        project.setId(1L);
        project.setProjectCode("SHM_EM_PUBLIC_SAMPLE");
        when(projectService.list(null, null)).thenReturn(Collections.singletonList(project));

        mockMvc.perform(get("/api/em/projects"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data[0].projectCode").value("SHM_EM_PUBLIC_SAMPLE"));
    }

    @Test
    public void projectFutureStateEndpointExposesExecutionDecision() throws Exception {
        PredictionExecutionGate gate = new PredictionExecutionGate();
        gate.setId(12L);
        gate.setExecutionMode("REPLAY");
        gate.setExecutionEligible(true);

        ProjectFutureState state = new ProjectFutureState();
        state.setProjectId(1L);
        state.setBatchId(7L);
        state.setExecutionMode("REPLAY");
        state.setExecutionEligible(true);
        state.setExecutionGate(gate);
        when(projectFutureStateService.get(
                ArgumentMatchers.eq(1L),
                ArgumentMatchers.eq(7L),
                ArgumentMatchers.eq(120),
                ArgumentMatchers.any(),
                ArgumentMatchers.isNull()))
                .thenReturn(state);

        mockMvc.perform(get("/api/em/projects/1/future-state")
                        .param("batchId", "7")
                        .param("horizonMinutes", "120")
                        .param("executionMode", "REPLAY"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.batchId").value(7))
                .andExpect(jsonPath("$.data.executionMode").value("REPLAY"))
                .andExpect(jsonPath("$.data.executionEligible").value(true))
                .andExpect(jsonPath("$.data.executionGate.id").value(12));
    }

    @Test
    public void predictionGateEndpointExposesReplayEligibility() throws Exception {
        LocalDateTime referenceTime = LocalDateTime.of(2026, 6, 24, 10, 5, 46);
        PredictionExecutionGate gate = new PredictionExecutionGate();
        gate.setId(12L);
        gate.setBatchId(7L);
        gate.setExecutionMode("REPLAY");
        gate.setExecutionEligible(true);
        when(predictionExecutionGateService.inspect(7L, PredictionExecutionMode.REPLAY, referenceTime))
                .thenReturn(gate);

        mockMvc.perform(get("/api/em/predictions/batches/7/execution-gate")
                        .param("mode", "REPLAY")
                        .param("referenceTime", "2026-06-24 10:05:46"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.batchId").value(7))
                .andExpect(jsonPath("$.data.executionMode").value("REPLAY"))
                .andExpect(jsonPath("$.data.executionEligible").value(true));
    }

    @Test
    public void lowFrequencyObservationEndpointUsesRegistryCode() throws Exception {
        LowFrequencyObservation observation = new LowFrequencyObservation();
        observation.setMetricCode("settlement");
        observation.setMetricValue(new BigDecimal("0.800000"));
        when(lowFrequencyObservationService.list(ArgumentMatchers.any(ObservationQuery.class)))
                .thenReturn(Collections.singletonList(observation));

        mockMvc.perform(get("/api/em/observations/low-frequency").param("registryCode", "LOW_STATIC_LEVEL"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data[0].metricCode").value("settlement"));
    }

    @Test
    public void accelerationWaveformEndpointUsesRegistryCode() throws Exception {
        AccelerationWaveform sample = new AccelerationWaveform();
        sample.setInstrumentId(2L);
        sample.setXAccel(0.08D);
        when(accelerationWaveformService.list(ArgumentMatchers.any(ObservationQuery.class)))
                .thenReturn(Collections.singletonList(sample));

        mockMvc.perform(get("/api/em/acceleration").param("registryCode", "ACC_1426000125"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data[0].instrumentId").value(2));
    }

    @Test
    public void ruleEvaluationEndpointIsSeparatedFromRuleCatalog() throws Exception {
        Map<String, Object> result = new HashMap<String, Object>();
        result.put("runId", 11L);
        result.put("eventCount", 1);
        when(eventEvaluationService.evaluate(ArgumentMatchers.any(RuleEvaluationRequest.class))).thenReturn(result);

        mockMvc.perform(post("/api/em/projects/1/rules/evaluate")
                        .contentType("application/json")
                        .content("{}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.eventCount").value(1));
    }
}





