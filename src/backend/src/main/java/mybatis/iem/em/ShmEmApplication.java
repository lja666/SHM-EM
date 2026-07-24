package mybatis.iem.em;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@MapperScan("mybatis.iem.em.modules.engineering.infrastructure.mapper")
@EnableScheduling
public class ShmEmApplication {
    public static void main(String[] args) {
        SpringApplication.run(ShmEmApplication.class, args);
    }
}





