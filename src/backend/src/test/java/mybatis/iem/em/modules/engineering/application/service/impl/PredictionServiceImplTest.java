package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.application.dto.PredictionQuery;
import mybatis.iem.em.modules.engineering.application.service.LowFrequencyObservationService;
import mybatis.iem.em.modules.engineering.application.service.PredictionExecutionGateService;
import mybatis.iem.em.modules.engineering.domain.model.LowFrequencyObservation;
import mybatis.iem.em.modules.engineering.domain.model.MetricSeriesPoint;
import mybatis.iem.em.modules.engineering.domain.model.PredictionBatch;
import mybatis.iem.em.modules.engineering.domain.model.PredictionDisplay;
import mybatis.iem.em.modules.engineering.domain.model.PredictionFeatureMapping;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.EventPredictionTraceMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.PredictionMapper;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import org.mockito.ArgumentCaptor;

public class PredictionServiceImplTest {

    @Test
    public void latestSelectsOneDeterministicBatchBeforeReadingResults() {
        PredictionMapper mapper = mock(PredictionMapper.class);
        LowFrequencyObservationService observationService = mock(LowFrequencyObservationService.class);
        EventPredictionTraceMapper traceMapper = mock(EventPredictionTraceMapper.class);
        PredictionExecutionGateService gateService = mock(PredictionExecutionGateService.class);
        PredictionServiceImpl service = new PredictionServiceImpl(mapper, observationService, traceMapper, gateService);

        PredictionBatch latestBatch = new PredictionBatch();
        latestBatch.setId(9L);
        latestBatch.setProjectId(1L);
        latestBatch.setBaseTime(LocalDateTime.of(2026, 6, 24, 10, 5, 46));
        when(mapper.selectBatches(any(PredictionQuery.class), eq(1)))
                .thenReturn(Collections.singletonList(latestBatch));

        PredictionDisplay row = new PredictionDisplay();
        row.setBatchId(9L);
        row.setStep(1);
        when(mapper.selectSeries(any(PredictionQuery.class), anyInt()))
                .thenReturn(Collections.singletonList(row));

        PredictionQuery query = new PredictionQuery();
        query.setProjectId(1L);
        query.setTargetType("Pressure");
        query.setFeatureCode("point3_0.12Pressure_value");

        List<PredictionDisplay> rows = service.latest(query);

        ArgumentCaptor<PredictionQuery> selectedQuery = ArgumentCaptor.forClass(PredictionQuery.class);
        verify(mapper).selectSeries(selectedQuery.capture(), eq(2000));
        assertEquals(9L, selectedQuery.getValue().getBatchId());
        assertEquals(1, rows.size());
    }

    @Test
    public void preservesObservationRegistryProvenanceInJointSeries() {
        PredictionMapper mapper = mock(PredictionMapper.class);
        LowFrequencyObservationService observationService = mock(LowFrequencyObservationService.class);
        EventPredictionTraceMapper traceMapper = mock(EventPredictionTraceMapper.class);
        PredictionExecutionGateService gateService = mock(PredictionExecutionGateService.class);
        PredictionServiceImpl service = new PredictionServiceImpl(mapper, observationService, traceMapper, gateService);

        PredictionFeatureMapping mapping = new PredictionFeatureMapping();
        mapping.setProjectId(1L);
        mapping.setFeatureCode("point1_0.8YD_value");
        mapping.setStationId(1L);
        mapping.setInstrumentId(11L);
        mapping.setSourceMetricCode("displacement_tilt_y_deg");
        mapping.setSourceRegistryCode("SHM_EM_PUBLIC_SAMPLE_DISPLACEMENT");
        when(mapper.selectFeatures(any(PredictionQuery.class), anyInt()))
                .thenReturn(Collections.singletonList(mapping));
        when(mapper.selectSeries(any(PredictionQuery.class), anyInt()))
                .thenReturn(Collections.emptyList());

        LowFrequencyObservation observation = new LowFrequencyObservation();
        observation.setProjectId(1L);
        observation.setStationId(1L);
        observation.setInstrumentId(11L);
        observation.setMetricCode("displacement_tilt_y_deg");
        observation.setObservedAt(LocalDateTime.of(2026, 6, 24, 10, 0));
        observation.setEngineeringValue(new BigDecimal("1.25"));
        observation.setEngineeringUnit("mm");
        observation.setSourceRegistryCode("SHM_EM_PUBLIC_SAMPLE_DISPLACEMENT");
        observation.setSourceRecordKey("obs:1");
        when(observationService.list(any())).thenReturn(Collections.singletonList(observation));

        PredictionQuery query = new PredictionQuery();
        query.setProjectId(1L);
        query.setBatchId(1L);
        query.setFeatureCode("point1_0.8YD_value");
        query.setIncludeObserved(true);

        List<MetricSeriesPoint> points = service.series(query);

        assertEquals(1, points.size());
        assertEquals("SHM_EM_PUBLIC_SAMPLE_DISPLACEMENT", points.get(0).getSourceRegistryCode());
        assertEquals("obs:1", points.get(0).getSourceRecordKey());
    }
}
