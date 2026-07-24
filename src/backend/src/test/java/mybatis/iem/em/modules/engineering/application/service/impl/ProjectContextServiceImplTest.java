package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.domain.model.Project;
import mybatis.iem.em.modules.engineering.domain.model.Station;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.InstrumentMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.ObservationTableRegistryMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.ProjectContextMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.ProjectMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.StationMapper;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.StationMetricMapper;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class ProjectContextServiceImplTest {
    @Test
    void usesDeclaredFieldPointCountWithoutHidingInternalStationRecordCount() {
        ProjectMapper projectMapper = mock(ProjectMapper.class);
        ProjectContextMapper contextMapper = mock(ProjectContextMapper.class);
        StationMapper stationMapper = mock(StationMapper.class);
        InstrumentMapper instrumentMapper = mock(InstrumentMapper.class);
        StationMetricMapper stationMetricMapper = mock(StationMetricMapper.class);
        ObservationTableRegistryMapper registryMapper = mock(ObservationTableRegistryMapper.class);

        Project project = new Project();
        project.setId(1L);
        project.setProjectCode("IEM_EXCAVATION_REAL");
        project.setProjectName("IEM Excavation Monitoring");
        project.setSpatialContextJson("{\"monitoringPointCount\":9}");
        when(projectMapper.selectById(1L)).thenReturn(project);

        List<Station> stations = new ArrayList<Station>();
        for (long id = 1; id <= 73; id++) {
            Station station = new Station();
            station.setId(id);
            station.setStationCode("INSTALLATION-" + id);
            station.setStationName("Installation record " + id);
            stations.add(station);
        }
        when(stationMapper.selectList(1L, 10000)).thenReturn(stations);
        when(instrumentMapper.selectList(1L, 10000)).thenReturn(Collections.emptyList());
        when(stationMetricMapper.selectList(1L, 20000)).thenReturn(Collections.emptyList());
        when(registryMapper.selectList(1L, 10000)).thenReturn(Collections.emptyList());

        ProjectContextServiceImpl service = new ProjectContextServiceImpl(
                projectMapper,
                contextMapper,
                stationMapper,
                instrumentMapper,
                stationMetricMapper,
                registryMapper
        );

        Map<String, Object> tree = service.objectTree(1L);

        assertEquals(9, tree.get("siteCount"));
        assertEquals(9, tree.get("stationCount"));
        assertEquals(73, tree.get("stationRecordCount"));
    }
}
