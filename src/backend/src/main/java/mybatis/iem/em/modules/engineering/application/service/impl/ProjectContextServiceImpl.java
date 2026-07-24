package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.common.BusinessException;
import mybatis.iem.em.modules.engineering.application.service.ProjectContextService;
import mybatis.iem.em.modules.engineering.domain.model.Instrument;
import mybatis.iem.em.modules.engineering.domain.model.ObservationTableRegistry;
import mybatis.iem.em.modules.engineering.domain.model.Project;
import mybatis.iem.em.modules.engineering.domain.model.Station;
import mybatis.iem.em.modules.engineering.domain.model.StationMetric;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.InstrumentMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.ObservationTableRegistryMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.ProjectContextMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.ProjectMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.StationMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.StationMetricMapper;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.time.OffsetDateTime;
import java.util.LinkedHashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class ProjectContextServiceImpl implements ProjectContextService {
    private static final Pattern SITE_NUMBER_PATTERN = Pattern.compile("(?:ST[-_ ]?|POINT[-_ ]?)?([1-9])(?:#|[^0-9]|$)", Pattern.CASE_INSENSITIVE);
    private static final Pattern MONITORING_POINT_COUNT_PATTERN = Pattern.compile("\\\"monitoringPointCount\\\"\\s*:\\s*([1-9][0-9]*)");

    private final ProjectMapper projectMapper;
    private final ProjectContextMapper contextMapper;
    private final StationMapper stationMapper;
    private final InstrumentMapper instrumentMapper;
    private final StationMetricMapper stationMetricMapper;
    private final ObservationTableRegistryMapper registryMapper;

    public ProjectContextServiceImpl(ProjectMapper projectMapper,
                                     ProjectContextMapper contextMapper,
                                     StationMapper stationMapper,
                                     InstrumentMapper instrumentMapper,
                                     StationMetricMapper stationMetricMapper,
                                     ObservationTableRegistryMapper registryMapper) {
        this.projectMapper = projectMapper;
        this.contextMapper = contextMapper;
        this.stationMapper = stationMapper;
        this.instrumentMapper = instrumentMapper;
        this.stationMetricMapper = stationMetricMapper;
        this.registryMapper = registryMapper;
    }

    @Override
    public Map<String, Object> overview() {
        Map<String, Object> result = new LinkedHashMap<String, Object>();
        List<Map<String, Object>> projects = contextMapper.selectProjectCards();
        result.put("projects", projects);
        result.put("projectCount", projects.size());
        result.put("dataSource", "database");
        result.put("generatedAt", OffsetDateTime.now().toString());
        result.put("statistics", overviewStatistics(projects));
        result.put("message", "Project overview is based on persisted SHM-EM records.");
        return result;
    }

    @Override
    public Map<String, Object> context(Long projectId) {
        Project project = requireProject(projectId);
        Map<String, Object> result = new LinkedHashMap<String, Object>();
        result.put("project", project);
        result.put("projectDisplay", projectDisplay(project));
        result.put("summary", contextMapper.selectProjectSummary(project.getId()));
        result.put("stationTypeCounts", contextMapper.selectStationTypeCounts(project.getId()));
        result.put("instrumentTypeCounts", contextMapper.selectInstrumentTypeCounts(project.getId()));
        result.put("metricCounts", contextMapper.selectMetricCounts(project.getId()));
        result.put("eventLevelCounts", contextMapper.selectEventLevelCounts(project.getId()));
        result.put("dataset", contextMapper.selectDatasetManifest(project.getId()));
        result.put("objectTreeUrl", "/api/em/projects/" + project.getId() + "/object-tree");
        return result;
    }

    @Override
    public Map<String, Object> objectTree(Long projectId) {
        Project project = requireProject(projectId);
        List<Station> stations = stationMapper.selectList(project.getId(), 10000);
        List<Instrument> instruments = instrumentMapper.selectList(project.getId(), 10000);
        List<StationMetric> stationMetrics = stationMetricMapper.selectList(project.getId(), 20000);
        List<ObservationTableRegistry> registries = registryMapper.selectList(project.getId(), 10000);
        return objectTreeResult(project, stations, instruments, stationMetrics, registries);
    }

    private Map<String, Object> objectTreeResult(Project project,
                                                 List<Station> stations,
                                                 List<Instrument> instruments,
                                                 List<StationMetric> stationMetrics,
                                                 List<ObservationTableRegistry> registries) {
        List<Map<String, Object>> stationNodes = new ArrayList<Map<String, Object>>();
        Set<String> siteNos = new LinkedHashSet<String>();
        for (Station station : stations) {
            Map<String, Object> stationNode = node("station", station.getId(), station.getStationCode(), safeName(station.getStationName(), station.getStationCode()));
            String siteNo = siteNoOf(station);
            if (siteNo != null) {
                siteNos.add(siteNo);
            }
            stationNode.put("siteNo", siteNo);
            stationNode.put("siteName", siteNo == null ? stationNode.get("name") : "Point " + siteNo);
            stationNode.put("stationType", station.getStationType());
            stationNode.put("status", station.getStatus());
            stationNode.put("instruments", instrumentNodes(station, instruments, stationMetrics, registries));
            stationNodes.add(stationNode);
        }
        Map<String, Object> result = new LinkedHashMap<String, Object>();
        result.put("project", projectDisplay(project));
        result.put("treeRole", "project-station-instrument-metric-registry");
        result.put("stations", stationNodes);
        Integer declaredSiteCount = declaredMonitoringPointCount(project);
        int siteCount = declaredSiteCount == null
                ? (siteNos.isEmpty() ? stations.size() : siteNos.size())
                : declaredSiteCount;
        result.put("siteCount", siteCount);
        result.put("stationCount", siteCount);
        result.put("stationRecordCount", stations.size());
        result.put("instrumentCount", instruments.size());
        result.put("acquisitionModuleCount", distinctInstrumentValueCount(instruments, true));
        result.put("dtuCount", distinctInstrumentValueCount(instruments, false));
        result.put("stationMetricCount", stationMetrics.size());
        result.put("registryCount", registries.size());
        return result;
    }

    private int distinctInstrumentValueCount(List<Instrument> instruments, boolean module) {
        Set<String> values = new LinkedHashSet<String>();
        for (Instrument instrument : instruments) {
            String value = module ? instrument.getModuleNo() : instrument.getDtuCode();
            if (value != null && !value.trim().isEmpty()) {
                values.add(value.trim());
            }
        }
        return values.size();
    }

    private Map<String, Object> overviewStatistics(List<Map<String, Object>> projects) {
        Map<String, Object> statistics = new LinkedHashMap<String, Object>();
        int totalProjects = projects == null ? 0 : projects.size();
        int activeProjects = 0;
        int warningProjects = 0;
        if (projects != null) {
            for (Map<String, Object> project : projects) {
                String status = String.valueOf(project.get("projectStatus") == null ? project.get("status") : project.get("projectStatus"));
                if ("active".equalsIgnoreCase(status) || "running".equalsIgnoreCase(status)) {
                    activeProjects++;
                }
                Number openEvents = numberValue(project.get("openEventCount"));
                if (openEvents != null && openEvents.longValue() > 0) {
                    warningProjects++;
                }
            }
        }
        statistics.put("totalProjects", totalProjects);
        statistics.put("activeProjects", activeProjects);
        statistics.put("warningProjects", warningProjects);
        statistics.put("eventStatusScope", "event_status NOT IN ('resolved','closed') for openEventCount where provided by mapper");
        return statistics;
    }

    private Number numberValue(Object value) {
        if (value instanceof Number) {
            return (Number) value;
        }
        if (value == null) {
            return null;
        }
        try {
            return Long.valueOf(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private List<Map<String, Object>> instrumentNodes(Station station,
                                                     List<Instrument> instruments,
                                                     List<StationMetric> stationMetrics,
                                                     List<ObservationTableRegistry> registries) {
        List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>();
        for (Instrument instrument : instruments) {
            if (!equalsLong(station.getId(), instrument.getStationId())) {
                continue;
            }
            Map<String, Object> item = node("instrument", instrument.getId(), instrument.getInstrumentCode(), safeName(instrument.getInstrumentName(), instrument.getInstrumentCode()));
            item.put("instrumentType", instrument.getInstrumentType());
            item.put("samplingMode", instrument.getSamplingMode());
            item.put("samplingFrequency", instrument.getSamplingFrequency());
            item.put("status", instrument.getStatus());
            item.put("metrics", metricNodes(instrument, stationMetrics, registries));
            rows.add(item);
        }
        return rows;
    }

    private List<Map<String, Object>> metricNodes(Instrument instrument,
                                                 List<StationMetric> stationMetrics,
                                                 List<ObservationTableRegistry> registries) {
        List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>();
        for (StationMetric stationMetric : stationMetrics) {
            if (!equalsLong(instrument.getId(), stationMetric.getInstrumentId())) {
                continue;
            }
            Map<String, Object> item = node("metric", stationMetric.getId(), stationMetric.getMetricCode(), safeName(stationMetric.getDisplayName(), stationMetric.getMetricCode()));
            item.put("metricUnit", stationMetric.getMetricUnit());
            item.put("baselineValue", stationMetric.getBaselineValue());
            item.put("warningEnabled", stationMetric.getWarningEnabled());
            item.put("registries", registryNodes(instrument, stationMetric, registries));
            rows.add(item);
        }
        return rows;
    }

    private List<Map<String, Object>> registryNodes(Instrument instrument,
                                                   StationMetric stationMetric,
                                                   List<ObservationTableRegistry> registries) {
        List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>();
        for (ObservationTableRegistry registry : registries) {
            if (registry.getInstrumentId() != null && !equalsLong(registry.getInstrumentId(), instrument.getId())) {
                continue;
            }
            if (registry.getInstrumentId() == null && registry.getMetricGroup() != null
                    && !registry.getMetricGroup().equals(stationMetric.getMetricCode())
                    && !registry.getMetricGroup().equals(instrument.getInstrumentType())) {
                continue;
            }
            Map<String, Object> item = node("registry", registry.getId(), registry.getRegistryCode(), registry.getLogicalSeriesName());
            item.put("storageBackend", registry.getStorageBackend());
            item.put("storageMode", registry.getStorageMode());
            item.put("sampleFrequencyHz", registry.getSampleFrequencyHz());
            item.put("enabled", registry.getEnabled());
            item.put("queryable", registry.getIsQueryable());
            item.put("eventSource", registry.getIsEventSource());
            rows.add(item);
        }
        return rows;
    }

    private Project requireProject(Long projectId) {
        if (projectId == null) throw new BusinessException("project id is required");
        Project project = projectMapper.selectById(projectId);
        if (project == null) {
            throw new BusinessException("project is not found: " + projectId);
        }
        return project;
    }

    private Map<String, Object> projectDisplay(Project project) {
        Map<String, Object> item = new LinkedHashMap<String, Object>();
        item.put("id", project.getId());
        item.put("projectCode", project.getProjectCode());
        item.put("projectName", project.getProjectName());
        item.put("displayName", safeName(project.getProjectName(), project.getProjectCode()));
        item.put("infrastructureType", project.getInfrastructureType());
        item.put("scenarioLabel", project.getScenarioLabel());
        item.put("status", project.getStatus());
        item.put("locationText", project.getLocationText());
        item.put("longitude", project.getLongitude());
        item.put("latitude", project.getLatitude());
        return item;
    }

    private Map<String, Object> node(String type, Long id, String code, String name) {
        Map<String, Object> item = new LinkedHashMap<String, Object>();
        item.put("type", type);
        item.put("id", id);
        item.put("code", code);
        item.put("name", safeName(name, code));
        return item;
    }

    private boolean equalsLong(Long a, Long b) {
        return a != null && a.equals(b);
    }

    private String safeName(String value, String fallbackValue) {
        return value == null || value.trim().isEmpty() ? fallbackValue : value;
    }

    private String siteNoOf(Station station) {
        String text = safeString(station.getStationCode()) + " "
                + safeString(station.getStationName()) + " "
                + safeString(station.getPositionDesc()) + " "
                + safeString(station.getStationType());
        Matcher matcher = SITE_NUMBER_PATTERN.matcher(text);
        return matcher.find() ? matcher.group(1) : null;
    }

    private Integer declaredMonitoringPointCount(Project project) {
        if (project == null || project.getSpatialContextJson() == null) {
            return null;
        }
        Matcher matcher = MONITORING_POINT_COUNT_PATTERN.matcher(project.getSpatialContextJson());
        return matcher.find() ? Integer.valueOf(matcher.group(1)) : null;
    }

    private String safeString(String value) {
        return value == null ? "" : value;
    }
}
