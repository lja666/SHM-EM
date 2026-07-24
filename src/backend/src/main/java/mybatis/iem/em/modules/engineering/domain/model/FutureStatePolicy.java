package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

@Data
public class FutureStatePolicy {
    private Long id;
    private Long projectId;
    private String policyCode;
    private String policyVersion;
    private String policyJson;
    private String policyHash;
    private Integer enabled;
}
