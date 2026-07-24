# Third-Party Notices

SHM-EM depends on third-party open-source packages. Their copyright and license
terms remain with their respective authors.

- Java dependencies are declared in `src/backend/pom.xml` and resolved by
  Maven, including Spring Boot, MyBatis, MySQL Connector/J, Druid, OpenPDF,
  Apache POI, JSON-java, Lombok, and springdoc-openapi.
- JavaScript dependencies and exact resolved versions are recorded in
  `src/frontend/package.json` and `src/frontend/package-lock.json`, including
  Vue, Element Plus, ECharts, Pinia, Axios, TypeScript, and Vite.
- Python dependencies and exact release versions are recorded in
  `src/pit_pre/requirements.lock.txt`, including PyTorch, NumPy, pandas,
  scikit-learn, joblib, and PyMySQL.
This file is an inventory pointer, not a replacement for the upstream license
texts. A public binary release should include the notices required by the
exact dependency versions resolved at release build time.
