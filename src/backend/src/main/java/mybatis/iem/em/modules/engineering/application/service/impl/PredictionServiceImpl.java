package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.application.dto.PredictionQuery;
import mybatis.iem.em.modules.engineering.application.service.PredictionService;
import mybatis.iem.em.modules.engineering.application.service.PredictionExecutionGateService;
import mybatis.iem.em.modules.engineering.application.service.LowFrequencyObservationService;
import mybatis.iem.em.modules.engineering.application.dto.ObservationQuery;
import mybatis.iem.em.common.BusinessException;
import mybatis.iem.em.modules.engineering.domain.model.PredictionBatch;
import mybatis.iem.em.modules.engineering.domain.model.PredictionBatchDetail;
import mybatis.iem.em.modules.engineering.domain.model.PredictionCompleteness;
import mybatis.iem.em.modules.engineering.domain.model.PredictionDisplay;
import mybatis.iem.em.modules.engineering.domain.model.PredictionFeatureMapping;
import mybatis.iem.em.modules.engineering.domain.model.PredictionModel;
import mybatis.iem.em.modules.engineering.domain.model.PredictionRun;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionGate;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionMode;
import mybatis.iem.em.modules.engineering.domain.model.MetricSeriesPoint;
import mybatis.iem.em.modules.engineering.domain.model.LowFrequencyObservation;
import mybatis.iem.em.modules.engineering.domain.model.EventPredictionTrace;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.EventPredictionTraceMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.PredictionMapper;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Service
public class PredictionServiceImpl implements PredictionService {
    private final PredictionMapper mapper;
    private final LowFrequencyObservationService observationService;
    private final EventPredictionTraceMapper traceMapper;
    private final PredictionExecutionGateService executionGateService;

    public PredictionServiceImpl(PredictionMapper mapper,
                                 LowFrequencyObservationService observationService,
                                 EventPredictionTraceMapper traceMapper,
                                 PredictionExecutionGateService executionGateService) {
        this.mapper = mapper;
        this.observationService = observationService;
        this.traceMapper = traceMapper;
        this.executionGateService = executionGateService;
    }

    @Override
    public List<PredictionBatch> batches(PredictionQuery query) {
        return mapper.selectBatches(ensureQuery(query), normalizeLimit(query == null ? null : query.getLimit(), 200));
    }

    @Override
    public List<PredictionModel> models(PredictionQuery query) {
        return mapper.selectModels(ensureQuery(query), normalizeLimit(query == null ? null : query.getLimit(), 200));
    }

    @Override
    public List<PredictionFeatureMapping> features(PredictionQuery query) {
        return mapper.selectFeatures(ensureQuery(query), normalizeLimit(query == null ? null : query.getLimit(), 500));
    }

    @Override
    public List<PredictionDisplay> latest(PredictionQuery query) {
        PredictionQuery effective = ensureQuery(query);
        if (effective.getBatchId() == null && isBlank(effective.getBatchCode())) {
            effective.setBatchId(resolveBatch(effective).getId());
        }
        return mapper.selectSeries(effective, normalizeLimit(effective.getLimit(), 2000));
    }

    @Override
    public PredictionBatchDetail batchDetail(Long batchId) {
        PredictionBatchDetail detail = new PredictionBatchDetail();
        detail.setBatch(requireBatch(batchId));
        detail.setRuns(runs(batchId));
        detail.setCompleteness(completeness(batchId));
        detail.setLinkedEventCount(traceMapper.countByBatchId(batchId));
        return detail;
    }

    @Override
    public List<PredictionRun> runs(Long batchId) {
        requireBatch(batchId);
        return mapper.selectRunsByBatch(batchId);
    }

    @Override
    public PredictionCompleteness completeness(Long batchId) {
        PredictionBatch batch = requireBatch(batchId);
        PredictionExecutionGate gate = executionGateService.inspect(batchId, PredictionExecutionMode.REPLAY, batch.getBaseTime());
        PredictionCompleteness result = new PredictionCompleteness();
        result.setGateId(gate.getId());
        result.setBatchId(gate.getBatchId());
        result.setBatchCode(gate.getBatchCode());
        result.setExpectedModels(gate.getExpectedModelCount());
        result.setActualModels(gate.getActualModelCount());
        result.setSuccessfulModels(gate.getSuccessfulModelCount());
        result.setExpectedSteps(gate.getExpectedSteps());
        result.setFeatureCount(gate.getExpectedFeatureCount());
        result.setExpectedPointCount(gate.getExpectedPointCount());
        result.setActualPointCount(gate.getActualPointCount());
        result.setMissingPointCount(gate.getMissingPointCount());
        result.setCompletenessPercent(percent(gate.getActualPointCount(), gate.getExpectedPointCount()));
        result.setComplete(Boolean.TRUE.equals(gate.getModelSetValid())
                && Boolean.TRUE.equals(gate.getFeatureSetValid())
                && Boolean.TRUE.equals(gate.getTimelineValid()));
        result.setBatchStatus(batch.getStatus());
        result.setInvalidTimestampCount(gate.getInvalidTimestampCount());
        result.setQualityIssueCount(gate.getQualityIssueCount());
        result.setExecutionEligible(gate.getExecutionEligible());
        result.setExecutionMode(gate.getExecutionMode());
        result.setModelSetValid(gate.getModelSetValid());
        result.setFeatureSetValid(gate.getFeatureSetValid());
        result.setTimelineValid(gate.getTimelineValid());
        result.setQualityValid(gate.getQualityValid());
        result.setArtifactHashValid(gate.getArtifactHashValid());
        result.setFreshnessValid(gate.getFreshnessValid());
        result.setIssues(new ArrayList<String>(gate.getIssues()));
        result.setTargets(new ArrayList<PredictionCompleteness.TargetCompleteness>(gate.getTargets()));
        return result;
    }

    @Override
    public List<MetricSeriesPoint> series(PredictionQuery query) {
        PredictionQuery effective = ensureQuery(query);
        List<MetricSeriesPoint> rows = new ArrayList<MetricSeriesPoint>();
        if (!Boolean.FALSE.equals(effective.getIncludeObserved())) {
            rows.addAll(observationPoints(effective));
        }
        rows.addAll(predictionSeries(effective));
        rows.sort(Comparator.comparing(MetricSeriesPoint::getTimestamp, Comparator.nullsLast(Comparator.naturalOrder())));
        return rows;
    }

    @Override
    public List<MetricSeriesPoint> predictionSeries(PredictionQuery query) {
        PredictionQuery effective = ensureQuery(query);
        if (effective.getBatchId() == null && isBlank(effective.getBatchCode())) {
            PredictionBatch batch = resolveBatch(effective);
            effective.setBatchId(batch.getId());
        }
        List<PredictionDisplay> source = mapper.selectSeries(effective, normalizeLimit(effective.getLimit(), 10000));
        boolean rawMode = "RAW".equalsIgnoreCase(effective.getValueMode());
        List<MetricSeriesPoint> rows = new ArrayList<MetricSeriesPoint>();
        for (PredictionDisplay item : source) {
            MetricSeriesPoint point = new MetricSeriesPoint();
            point.setProjectId(item.getProjectId());
            point.setStationId(item.getStationId());
            point.setInstrumentId(item.getInstrumentId());
            point.setMetricCode(rawMode || item.getEngineeringMetricCode() == null ? item.getMetricCode() : item.getEngineeringMetricCode());
            point.setEngineeringMetricCode(item.getEngineeringMetricCode());
            point.setTimestamp(item.getFutureTime());
            point.setRawValue(item.getRawPredictedValue());
            point.setRawUnit(item.getRawPredictedUnit());
            point.setEngineeringValue(item.getEngineeringValue());
            point.setEngineeringUnit(item.getEngineeringUnit());
            point.setValue(rawMode ? item.getRawPredictedValue() : item.getEngineeringValue());
            point.setUnit(rawMode ? item.getRawPredictedUnit() : item.getEngineeringUnit());
            point.setValueMode(rawMode ? "RAW" : "ENGINEERING");
            point.setConversionOperatorCode(item.getConversionOperatorCode());
            point.setConversionVersion(item.getConversionVersion());
            point.setConversionStatus(item.getConversionStatus());
            point.setConversionRemark(item.getConversionRemark());
            point.setQualityFlag(item.getQualityFlag());
            point.setSourceType("PREDICTION");
            point.setSourceRecordKey(item.getSourceRecordKey());
            point.setSourceBatchId(item.getBatchId());
            point.setSourceBatchCode(item.getBatchCode());
            point.setSourceRunId(item.getRunId());
            point.setSourceModelId(item.getModelId());
            point.setSourceModelCode(item.getModelCode());
            point.setSourceModelVersion(item.getModelVersion());
            point.setTargetType(item.getTargetType());
            point.setFeatureCode(item.getFeatureCode());
            point.setFeatureLabel(item.getFeatureLabel());
            point.setStep(item.getStep());
            point.setHorizonMinutes(item.getHorizonMinutes());
            point.setOriginTime(item.getBaseTime());
            point.setLowerBound(rawMode ? item.getRawLowerBound() : item.getLowerBound());
            point.setUpperBound(rawMode ? item.getRawUpperBound() : item.getUpperBound());
            point.setConfidence(item.getConfidence());
            point.setResultHash(isBlank(item.getRunResultHash()) ? item.getBatchOutputHash() : item.getRunResultHash());
            rows.add(point);
        }
        return rows;
    }

    @Override
    public PredictionBatch resolveBatch(PredictionQuery query) {
        PredictionQuery effective = ensureQuery(query);
        if (effective.getBatchId() != null) {
            return requireBatch(effective.getBatchId());
        }
        List<PredictionBatch> rows = mapper.selectBatches(effective, 1);
        if (rows.isEmpty()) {
            throw new BusinessException("No prediction batch matches the current context");
        }
        return rows.get(0);
    }

    @Override
    public EventPredictionTrace eventTrace(Long eventId) {
        EventPredictionTrace trace = traceMapper.selectByEventId(eventId);
        if (trace == null) {
            throw new BusinessException("No prediction trace is associated with event " + eventId);
        }
        return trace;
    }

    private List<MetricSeriesPoint> observationPoints(PredictionQuery query) {
        PredictionFeatureMapping feature = resolveFeatureMapping(query);
        ObservationQuery observationQuery = new ObservationQuery();
        observationQuery.setProjectId(firstNonNull(query.getProjectId(), feature == null ? null : feature.getProjectId()));
        observationQuery.setStationId(firstNonNull(query.getStationId(), feature == null ? null : feature.getStationId()));
        observationQuery.setStationIds(query.getStationIds());
        observationQuery.setInstrumentId(firstNonNull(query.getInstrumentId(), feature == null ? null : feature.getInstrumentId()));
        observationQuery.setInstrumentIds(query.getInstrumentIds());
        observationQuery.setInstrumentType(query.getInstrumentType());
        observationQuery.setMetricCode(firstText(query.getMetricCode(), feature == null ? null : feature.getSourceMetricCode()));
        observationQuery.setRegistryCode(firstText(query.getRegistryCode(), feature == null ? null : feature.getSourceRegistryCode()));
        observationQuery.setStartTime(query.getStartTime());
        observationQuery.setEndTime(query.getEndTime());
        observationQuery.setLimit(normalizeLimit(query.getLimit(), 5000));
        List<LowFrequencyObservation> source = observationService.list(observationQuery);
        boolean rawMode = "RAW".equalsIgnoreCase(query.getValueMode());
        List<MetricSeriesPoint> rows = new ArrayList<MetricSeriesPoint>();
        for (LowFrequencyObservation item : source) {
            MetricSeriesPoint point = new MetricSeriesPoint();
            point.setProjectId(item.getProjectId());
            point.setStationId(item.getStationId());
            point.setInstrumentId(item.getInstrumentId());
            point.setMetricCode(rawMode || item.getEngineeringMetricCode() == null ? item.getMetricCode() : item.getEngineeringMetricCode());
            point.setEngineeringMetricCode(item.getEngineeringMetricCode());
            point.setTimestamp(item.getObservedAt());
            point.setRawValue(item.getRawValue());
            point.setRawUnit(item.getRawUnit());
            point.setEngineeringValue(item.getEngineeringValue());
            point.setEngineeringUnit(item.getEngineeringUnit());
            point.setValue(rawMode ? item.getRawValue() : item.getEngineeringValue());
            point.setUnit(rawMode ? item.getRawUnit() : item.getEngineeringUnit());
            point.setValueMode(rawMode ? "RAW" : "ENGINEERING");
            point.setBaselineValue(item.getBaselineValue());
            point.setQualityFlag(item.getQualityFlag());
            point.setConversionOperatorCode(item.getConversionOperatorCode());
            point.setConversionVersion(item.getConversionVersion());
            point.setConversionStatus(item.getConversionStatus());
            point.setConversionRemark(item.getConversionRemark());
            point.setSourceType("OBSERVATION");
            point.setSourceRegistryCode(item.getSourceRegistryCode());
            point.setSourceRecordKey(item.getSourceRecordKey());
            rows.add(point);
        }
        return rows;
    }

    private PredictionFeatureMapping resolveFeatureMapping(PredictionQuery query) {
        if (isBlank(query.getFeatureCode())) return null;
        List<PredictionFeatureMapping> mappings = mapper.selectFeatures(query, 2);
        if (mappings.isEmpty()) {
            throw new BusinessException("Prediction feature mapping not found: " + query.getFeatureCode());
        }
        if (mappings.size() > 1) {
            throw new BusinessException("Prediction feature mapping is ambiguous: " + query.getFeatureCode());
        }
        return mappings.get(0);
    }

    private <T> T firstNonNull(T preferred, T fallback) {
        return preferred == null ? fallback : preferred;
    }

    private String firstText(String preferred, String fallback) {
        return isBlank(preferred) ? fallback : preferred;
    }

    private PredictionBatch requireBatch(Long batchId) {
        PredictionBatch batch = batchId == null ? null : mapper.selectBatchById(batchId);
        if (batch == null) {
            throw new BusinessException("Prediction batch not found: " + batchId);
        }
        return batch;
    }

    private BigDecimal percent(int actual, int expected) {
        if (expected <= 0) return BigDecimal.ZERO;
        return BigDecimal.valueOf(actual)
                .multiply(BigDecimal.valueOf(100))
                .divide(BigDecimal.valueOf(expected), 1, RoundingMode.HALF_UP);
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private PredictionQuery ensureQuery(PredictionQuery query) {
        return query == null ? new PredictionQuery() : query;
    }

    private Integer normalizeLimit(Integer limit, int defaultLimit) {
        if (limit == null || limit <= 0) {
            return defaultLimit;
        }
        return Math.min(limit, 50000);
    }
}
