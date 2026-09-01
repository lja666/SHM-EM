ARG DOCKERHUB_PREFIX=

FROM ${DOCKERHUB_PREFIX}maven:3.9.11-eclipse-temurin-8 AS source
WORKDIR /workspace/backend
COPY src/backend/pom.xml ./
RUN mvn -q -DskipTests dependency:go-offline
COPY src/backend/src ./src
COPY src/pit_pre/tests/fixtures ../pit_pre/tests/fixtures

FROM source AS test
RUN mvn -q test

FROM test AS package
RUN mvn -q -DskipTests package

FROM ${DOCKERHUB_PREFIX}eclipse-temurin:8-jre-jammy AS runtime
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin shm-em
WORKDIR /app
COPY --from=package /workspace/backend/target/SHM-EM-1.0.1.jar /app/shm-em.jar
RUN mkdir -p /app/report-files && chown -R shm-em:shm-em /app
USER shm-em
EXPOSE 5101
ENTRYPOINT ["java", "-jar", "/app/shm-em.jar"]
