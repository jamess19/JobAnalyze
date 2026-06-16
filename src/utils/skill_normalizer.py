"""
SkillNormalizer - Centralized skill normalization and category assignment.

Single source of truth for:
- Canonical skill names (e.g., "reactjs" → "React")
- Synonym merging (e.g., "Amazon Web Services" → "AWS")
- Category classification (e.g., "Python" → "PROGRAMMING LANGUAGES")
"""

import logging
import os
from collections import Counter
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================
#  SKILL_CATEGORY_MAP: canonical_name → category
# ============================================================
SKILL_CATEGORY_MAP: dict[str, str] = {
    # --- PROGRAMMING LANGUAGES ---
    "Python": "PROGRAMMING LANGUAGES",
    "Java": "PROGRAMMING LANGUAGES",
    "JavaScript": "PROGRAMMING LANGUAGES",
    "TypeScript": "PROGRAMMING LANGUAGES",
    "C#": "PROGRAMMING LANGUAGES",
    "C++": "PROGRAMMING LANGUAGES",
    "C/C++": "PROGRAMMING LANGUAGES",
    "Go": "PROGRAMMING LANGUAGES",
    "Rust": "PROGRAMMING LANGUAGES",
    "Kotlin": "PROGRAMMING LANGUAGES",
    "Swift": "PROGRAMMING LANGUAGES",
    "Scala": "PROGRAMMING LANGUAGES",
    "R": "PROGRAMMING LANGUAGES",
    "Ruby": "PROGRAMMING LANGUAGES",
    "PHP": "PROGRAMMING LANGUAGES",
    "Dart": "PROGRAMMING LANGUAGES",
    "Perl": "PROGRAMMING LANGUAGES",
    "Objective-C": "PROGRAMMING LANGUAGES",
    "Groovy": "PROGRAMMING LANGUAGES",
    "Cobol": "PROGRAMMING LANGUAGES",
    "Assembly": "PROGRAMMING LANGUAGES",
    "VBA": "PROGRAMMING LANGUAGES",
    "PL/SQL": "PROGRAMMING LANGUAGES",
    "T-SQL": "PROGRAMMING LANGUAGES",
    "Shell": "PROGRAMMING LANGUAGES",
    "Bash": "PROGRAMMING LANGUAGES",
    "PowerShell": "PROGRAMMING LANGUAGES",
    "Matlab": "PROGRAMMING LANGUAGES",
    "SQL": "PROGRAMMING LANGUAGES",
    "Elixir": "PROGRAMMING LANGUAGES",
    "Haskell": "PROGRAMMING LANGUAGES",
    "Lua": "PROGRAMMING LANGUAGES",

    # --- FRONTEND - HTML/CSS/JS BASICS ---
    "HTML": "FRONTEND - HTML/CSS/JS BASICS",
    "HTML5": "FRONTEND - HTML/CSS/JS BASICS",
    "CSS": "FRONTEND - HTML/CSS/JS BASICS",
    "CSS3": "FRONTEND - HTML/CSS/JS BASICS",
    "SASS": "FRONTEND - HTML/CSS/JS BASICS",
    "SCSS": "FRONTEND - HTML/CSS/JS BASICS",
    "Bootstrap": "FRONTEND - HTML/CSS/JS BASICS",
    "Tailwind CSS": "FRONTEND - HTML/CSS/JS BASICS",
    "Foundation": "FRONTEND - HTML/CSS/JS BASICS",
    "HTMX": "FRONTEND - HTML/CSS/JS BASICS",

    # --- FRONTEND FRAMEWORKS & LIBRARIES ---
    "React": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Vue": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Vue.js": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Angular": "FRONTEND FRAMEWORKS & LIBRARIES",
    "AngularJS": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Svelte": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Next.js": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Nuxt.js": "FRONTEND FRAMEWORKS & LIBRARIES",
    "jQuery": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Redux": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Vuex": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Pinia": "FRONTEND FRAMEWORKS & LIBRARIES",
    "NgRx": "FRONTEND FRAMEWORKS & LIBRARIES",
    "RxJS": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Material UI": "FRONTEND FRAMEWORKS & LIBRARIES",
    "MUI": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Ant Design": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Remix": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Backbone.js": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Webpack": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Vite": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Rollup": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Gulp": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Grunt": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Flux": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Styled Components": "FRONTEND FRAMEWORKS & LIBRARIES",
    "React Router": "FRONTEND FRAMEWORKS & LIBRARIES",
    "React Query": "FRONTEND FRAMEWORKS & LIBRARIES",
    "NPM": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Yarn": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Parcel": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Babel": "FRONTEND FRAMEWORKS & LIBRARIES",
    "esbuild": "FRONTEND FRAMEWORKS & LIBRARIES",
    "Chakra UI": "FRONTEND FRAMEWORKS & LIBRARIES",
    "pnpm": "FRONTEND FRAMEWORKS & LIBRARIES",

    # --- BACKEND FRAMEWORKS & LIBRARIES ---
    "Node.js": "BACKEND FRAMEWORKS & LIBRARIES",
    "Express": "BACKEND FRAMEWORKS & LIBRARIES",
    "NestJS": "BACKEND FRAMEWORKS & LIBRARIES",
    "Fastify": "BACKEND FRAMEWORKS & LIBRARIES",
    "Koa": "BACKEND FRAMEWORKS & LIBRARIES",
    "Spring": "BACKEND FRAMEWORKS & LIBRARIES",
    "Spring Boot": "BACKEND FRAMEWORKS & LIBRARIES",
    "Spring MVC": "BACKEND FRAMEWORKS & LIBRARIES",
    "Spring Cloud": "BACKEND FRAMEWORKS & LIBRARIES",
    "Spring Security": "BACKEND FRAMEWORKS & LIBRARIES",
    "Spring Data": "BACKEND FRAMEWORKS & LIBRARIES",
    ".NET": "BACKEND FRAMEWORKS & LIBRARIES",
    ".NET Core": "BACKEND FRAMEWORKS & LIBRARIES",
    "ASP.NET": "BACKEND FRAMEWORKS & LIBRARIES",
    "ASP.NET Core": "BACKEND FRAMEWORKS & LIBRARIES",
    "Entity Framework": "BACKEND FRAMEWORKS & LIBRARIES",
    "EF Core": "BACKEND FRAMEWORKS & LIBRARIES",
    "Blazor": "BACKEND FRAMEWORKS & LIBRARIES",
    "Django": "BACKEND FRAMEWORKS & LIBRARIES",
    "Flask": "BACKEND FRAMEWORKS & LIBRARIES",
    "FastAPI": "BACKEND FRAMEWORKS & LIBRARIES",
    "Tornado": "BACKEND FRAMEWORKS & LIBRARIES",
    "Celery": "BACKEND FRAMEWORKS & LIBRARIES",
    "Ruby on Rails": "BACKEND FRAMEWORKS & LIBRARIES",
    "Laravel": "BACKEND FRAMEWORKS & LIBRARIES",
    "Symfony": "BACKEND FRAMEWORKS & LIBRARIES",
    "CodeIgniter": "BACKEND FRAMEWORKS & LIBRARIES",
    "CakePHP": "BACKEND FRAMEWORKS & LIBRARIES",
    "Zend": "BACKEND FRAMEWORKS & LIBRARIES",
    "Yii": "BACKEND FRAMEWORKS & LIBRARIES",
    "WordPress": "BACKEND FRAMEWORKS & LIBRARIES",
    "Drupal": "BACKEND FRAMEWORKS & LIBRARIES",
    "Magento": "BACKEND FRAMEWORKS & LIBRARIES",
    "PrestaShop": "BACKEND FRAMEWORKS & LIBRARIES",
    "Hibernate": "BACKEND FRAMEWORKS & LIBRARIES",
    "JPA": "BACKEND FRAMEWORKS & LIBRARIES",
    "SQLAlchemy": "BACKEND FRAMEWORKS & LIBRARIES",
    "Quarkus": "BACKEND FRAMEWORKS & LIBRARIES",
    "Struts": "BACKEND FRAMEWORKS & LIBRARIES",
    "JSF": "BACKEND FRAMEWORKS & LIBRARIES",
    "Gin": "BACKEND FRAMEWORKS & LIBRARIES",
    "Echo": "BACKEND FRAMEWORKS & LIBRARIES",
    "Fiber": "BACKEND FRAMEWORKS & LIBRARIES",
    "Supabase": "BACKEND FRAMEWORKS & LIBRARIES",
    "PHPUnit": "BACKEND FRAMEWORKS & LIBRARIES",
    "Composer": "BACKEND FRAMEWORKS & LIBRARIES",
    "aiohttp": "BACKEND FRAMEWORKS & LIBRARIES",

    # --- MOBILE DEVELOPMENT ---
    "Flutter": "MOBILE DEVELOPMENT",
    "React Native": "MOBILE DEVELOPMENT",
    "SwiftUI": "MOBILE DEVELOPMENT",
    "UIKit": "MOBILE DEVELOPMENT",
    "Jetpack Compose": "MOBILE DEVELOPMENT",
    "Kotlin Multiplatform": "MOBILE DEVELOPMENT",
    "KMM": "MOBILE DEVELOPMENT",
    "Android": "MOBILE DEVELOPMENT",
    "Android Studio": "MOBILE DEVELOPMENT",
    "Android SDK": "MOBILE DEVELOPMENT",
    "iOS": "MOBILE DEVELOPMENT",
    "iOS SDK": "MOBILE DEVELOPMENT",
    "Xcode": "MOBILE DEVELOPMENT",
    "Ionic": "MOBILE DEVELOPMENT",
    "Capacitor": "MOBILE DEVELOPMENT",
    "Expo": "MOBILE DEVELOPMENT",
    "Mobile App": "MOBILE DEVELOPMENT",
    "Progressive Web App": "MOBILE DEVELOPMENT",
    "Espresso": "MOBILE DEVELOPMENT",
    "Detox": "MOBILE DEVELOPMENT",
    "XCTest": "MOBILE DEVELOPMENT",
    "Cordova": "MOBILE DEVELOPMENT",
    "Xamarin": "MOBILE DEVELOPMENT",
    "MAUI": "MOBILE DEVELOPMENT",
    "KMP": "MOBILE DEVELOPMENT",
    "PWA": "MOBILE DEVELOPMENT",

    # --- DATABASES ---
    "MySQL": "DATABASES",
    "PostgreSQL": "DATABASES",
    "MongoDB": "DATABASES",
    "Redis": "DATABASES",
    "Oracle": "DATABASES",
    "Oracle DB": "DATABASES",
    "MS SQL Server": "DATABASES",
    "MariaDB": "DATABASES",
    "SQLite": "DATABASES",
    "Cassandra": "DATABASES",
    "Neo4j": "DATABASES",
    "DynamoDB": "DATABASES",
    "CouchBase": "DATABASES",
    "Elasticsearch": "DATABASES",
    "HBase": "DATABASES",
    "CockroachDB": "DATABASES",
    "CosmosDB": "DATABASES",
    "DB2": "DATABASES",
    "Teradata": "DATABASES",
    "Vertica": "DATABASES",
    "ClickHouse": "DATABASES",
    "Memcached": "DATABASES",
    "ElastiCache": "DATABASES",
    "Firestore": "DATABASES",
    "Firebase": "DATABASES",
    "NoSQL": "DATABASES",
    "SSIS": "DATABASES",

    # --- DATA ENGINEERING & ANALYTICS ---
    "Spark": "DATA ENGINEERING & ANALYTICS",
    "PySpark": "DATA ENGINEERING & ANALYTICS",
    "Hadoop": "DATA ENGINEERING & ANALYTICS",
    "Kafka": "DATA ENGINEERING & ANALYTICS",
    "Airflow": "DATA ENGINEERING & ANALYTICS",
    "Flink": "DATA ENGINEERING & ANALYTICS",
    "Pandas": "DATA ENGINEERING & ANALYTICS",
    "NumPy": "DATA ENGINEERING & ANALYTICS",
    "Matplotlib": "DATA ENGINEERING & ANALYTICS",
    "Seaborn": "DATA ENGINEERING & ANALYTICS",
    "Plotly": "DATA ENGINEERING & ANALYTICS",
    "SciPy": "DATA ENGINEERING & ANALYTICS",
    "Hive": "DATA ENGINEERING & ANALYTICS",
    "Presto": "DATA ENGINEERING & ANALYTICS",
    "Trino": "DATA ENGINEERING & ANALYTICS",
    "Impala": "DATA ENGINEERING & ANALYTICS",
    "Databricks": "DATA ENGINEERING & ANALYTICS",
    "Snowflake": "DATA ENGINEERING & ANALYTICS",
    "BigQuery": "DATA ENGINEERING & ANALYTICS",
    "Redshift": "DATA ENGINEERING & ANALYTICS",
    "Data Warehouse": "DATA ENGINEERING & ANALYTICS",
    "Data Lake": "DATA ENGINEERING & ANALYTICS",
    "Data Mesh": "DATA ENGINEERING & ANALYTICS",
    "Delta Lake": "DATA ENGINEERING & ANALYTICS",
    "Lakehouse": "DATA ENGINEERING & ANALYTICS",
    "Data Pipeline": "DATA ENGINEERING & ANALYTICS",
    "ETL": "DATA ENGINEERING & ANALYTICS",
    "ELT": "DATA ENGINEERING & ANALYTICS",
    "DBT": "DATA ENGINEERING & ANALYTICS",
    "Informatica": "DATA ENGINEERING & ANALYTICS",
    "Talend": "DATA ENGINEERING & ANALYTICS",
    "NiFi": "DATA ENGINEERING & ANALYTICS",
    "Pentaho": "DATA ENGINEERING & ANALYTICS",
    "AWS Glue": "DATA ENGINEERING & ANALYTICS",
    "Glue": "DATA ENGINEERING & ANALYTICS",
    "Azure Data Factory": "DATA ENGINEERING & ANALYTICS",
    "EMR": "DATA ENGINEERING & ANALYTICS",
    "Airbyte": "DATA ENGINEERING & ANALYTICS",
    "Fivetran": "DATA ENGINEERING & ANALYTICS",
    "Luigi": "DATA ENGINEERING & ANALYTICS",
    "Dagster": "DATA ENGINEERING & ANALYTICS",
    "Prefect": "DATA ENGINEERING & ANALYTICS",
    "Apache Beam": "DATA ENGINEERING & ANALYTICS",
    "Apache Storm": "DATA ENGINEERING & ANALYTICS",
    "Dataflow": "DATA ENGINEERING & ANALYTICS",
    "Dataproc": "DATA ENGINEERING & ANALYTICS",
    "Power BI": "DATA ENGINEERING & ANALYTICS",
    "Tableau": "DATA ENGINEERING & ANALYTICS",
    "Looker": "DATA ENGINEERING & ANALYTICS",
    "Metabase": "DATA ENGINEERING & ANALYTICS",
    "Superset": "DATA ENGINEERING & ANALYTICS",
    "Redash": "DATA ENGINEERING & ANALYTICS",
    "Qlik": "DATA ENGINEERING & ANALYTICS",
    "QlikView": "DATA ENGINEERING & ANALYTICS",
    "Google Sheets": "DATA ENGINEERING & ANALYTICS",
    "Excel": "DATA ENGINEERING & ANALYTICS",
    "Mode": "DATA ENGINEERING & ANALYTICS",
    "Athena": "DATA ENGINEERING & ANALYTICS",
    "Azure Synapse": "DATA ENGINEERING & ANALYTICS",
    "Synapse": "DATA ENGINEERING & ANALYTICS",

    # --- MACHINE LEARNING & AI ---
    "TensorFlow": "MACHINE LEARNING & AI",
    "PyTorch": "MACHINE LEARNING & AI",
    "Keras": "MACHINE LEARNING & AI",
    "Scikit-learn": "MACHINE LEARNING & AI",
    "XGBoost": "MACHINE LEARNING & AI",
    "LightGBM": "MACHINE LEARNING & AI",
    "CatBoost": "MACHINE LEARNING & AI",
    "Hugging Face": "MACHINE LEARNING & AI",
    "LLM": "MACHINE LEARNING & AI",
    "GPT": "MACHINE LEARNING & AI",
    "OpenAI": "MACHINE LEARNING & AI",
    "ChatGPT": "MACHINE LEARNING & AI",
    "LangChain": "MACHINE LEARNING & AI",
    "RAG": "MACHINE LEARNING & AI",
    "MLflow": "MACHINE LEARNING & AI",
    "MLOps": "MACHINE LEARNING & AI",
    "Kubeflow": "MACHINE LEARNING & AI",
    "SageMaker": "MACHINE LEARNING & AI",
    "Azure ML": "MACHINE LEARNING & AI",
    "Azure Machine Learning": "MACHINE LEARNING & AI",
    "Vertex AI": "MACHINE LEARNING & AI",
    "Computer Vision": "MACHINE LEARNING & AI",
    "Image Processing": "MACHINE LEARNING & AI",
    "BERT": "MACHINE LEARNING & AI",
    "Transformers": "MACHINE LEARNING & AI",
    "ONNX": "MACHINE LEARNING & AI",
    "TensorRT": "MACHINE LEARNING & AI",
    "Triton": "MACHINE LEARNING & AI",
    "SpaCy": "MACHINE LEARNING & AI",
    "NLTK": "MACHINE LEARNING & AI",
    "Ray": "MACHINE LEARNING & AI",
    "JAX": "MACHINE LEARNING & AI",
    "Mxnet": "MACHINE LEARNING & AI",
    "Google Colab": "MACHINE LEARNING & AI",
    "Jupyter": "MACHINE LEARNING & AI",
    "Jupyter Notebook": "MACHINE LEARNING & AI",
    "DVC": "MACHINE LEARNING & AI",
    "Detectron": "MACHINE LEARNING & AI",
    "OpenCV": "MACHINE LEARNING & AI",
    "YOLO": "MACHINE LEARNING & AI",
    "Neptune": "MACHINE LEARNING & AI",
    "FAISS": "MACHINE LEARNING & AI",
    "Milvus": "MACHINE LEARNING & AI",
    "Pinecone": "MACHINE LEARNING & AI",
    "Weaviate": "MACHINE LEARNING & AI",
    "Chroma": "MACHINE LEARNING & AI",
    "Vector Database": "MACHINE LEARNING & AI",
    "AI": "MACHINE LEARNING & AI",
    "ML": "MACHINE LEARNING & AI",
    "Machine Learning": "MACHINE LEARNING & AI",
    "Deep Learning": "MACHINE LEARNING & AI",
    "NLP": "MACHINE LEARNING & AI",
    "Weights & Biases": "MACHINE LEARNING & AI",

    # --- CLOUD PLATFORMS ---
    "AWS": "CLOUD PLATFORMS",
    "Azure": "CLOUD PLATFORMS",
    "GCP": "CLOUD PLATFORMS",
    "IBM Cloud": "CLOUD PLATFORMS",
    "DigitalOcean": "CLOUD PLATFORMS",
    "Vercel": "CLOUD PLATFORMS",
    "Railway": "CLOUD PLATFORMS",
    "Cloudflare": "CLOUD PLATFORMS",
    "EC2": "CLOUD PLATFORMS",
    "S3": "CLOUD PLATFORMS",
    "RDS": "CLOUD PLATFORMS",
    "Lambda": "CLOUD PLATFORMS",
    "AWS Lambda": "CLOUD PLATFORMS",
    "ECS": "CLOUD PLATFORMS",
    "EKS": "CLOUD PLATFORMS",
    "Fargate": "CLOUD PLATFORMS",
    "CloudWatch": "CLOUD PLATFORMS",
    "SNS": "CLOUD PLATFORMS",
    "SQS": "CLOUD PLATFORMS",
    "Kinesis": "CLOUD PLATFORMS",
    "Step Functions": "CLOUD PLATFORMS",
    "Cognito": "CLOUD PLATFORMS",
    "CloudFormation": "CLOUD PLATFORMS",
    "AWS CDK": "CLOUD PLATFORMS",
    "AWS SAM": "CLOUD PLATFORMS",
    "Cloud SQL": "CLOUD PLATFORMS",
    "Cloud Functions": "CLOUD PLATFORMS",
    "Cloud Storage": "CLOUD PLATFORMS",
    "GKE": "CLOUD PLATFORMS",
    "AKS": "CLOUD PLATFORMS",
    "Azure Blob": "CLOUD PLATFORMS",
    "Azure Functions": "CLOUD PLATFORMS",
    "Azure Pipelines": "CLOUD PLATFORMS",
    "Azure DevOps": "CLOUD PLATFORMS",
    "Serverless": "CLOUD PLATFORMS",
    "Serverless Framework": "CLOUD PLATFORMS",
    "FaaS": "CLOUD PLATFORMS",
    "Pub/Sub": "CLOUD PLATFORMS",
    "Alibaba Cloud": "CLOUD PLATFORMS",
    "Cloud Run": "CLOUD PLATFORMS",
    "Heroku": "CLOUD PLATFORMS",
    "Linode": "CLOUD PLATFORMS",
    "Oracle Cloud": "CLOUD PLATFORMS",
    "Netlify": "CLOUD PLATFORMS",
    "Azure Service Bus": "CLOUD PLATFORMS",

    # --- DEVOPS & CI/CD ---
    "Docker": "DEVOPS & CI/CD",
    "Docker Compose": "DEVOPS & CI/CD",
    "Docker Swarm": "DEVOPS & CI/CD",
    "Kubernetes": "DEVOPS & CI/CD",
    "Helm": "DEVOPS & CI/CD",
    "Kustomize": "DEVOPS & CI/CD",
    "Istio": "DEVOPS & CI/CD",
    "Linkerd": "DEVOPS & CI/CD",
    "Envoy": "DEVOPS & CI/CD",
    "Jenkins": "DEVOPS & CI/CD",
    "Terraform": "DEVOPS & CI/CD",
    "Ansible": "DEVOPS & CI/CD",
    "Pulumi": "DEVOPS & CI/CD",
    "Chef": "DEVOPS & CI/CD",
    "Puppet": "DEVOPS & CI/CD",
    "CI/CD": "DEVOPS & CI/CD",
    "GitHub Actions": "DEVOPS & CI/CD",
    "GitLab CI": "DEVOPS & CI/CD",
    "CircleCI": "DEVOPS & CI/CD",
    "ArgoCD": "DEVOPS & CI/CD",
    "Bamboo": "DEVOPS & CI/CD",
    "TeamCity": "DEVOPS & CI/CD",
    "Tekton": "DEVOPS & CI/CD",
    "Crossplane": "DEVOPS & CI/CD",
    "Nomad": "DEVOPS & CI/CD",
    "Packer": "DEVOPS & CI/CD",
    "Rancher": "DEVOPS & CI/CD",
    "Podman": "DEVOPS & CI/CD",
    "DevOps": "DEVOPS & CI/CD",
    "DevSecOps": "DEVOPS & CI/CD",
    "SRE": "DEVOPS & CI/CD",
    "Prometheus": "DEVOPS & CI/CD",
    "Grafana": "DEVOPS & CI/CD",
    "Datadog": "DEVOPS & CI/CD",
    "New Relic": "DEVOPS & CI/CD",
    "Kibana": "DEVOPS & CI/CD",
    "ELK Stack": "DEVOPS & CI/CD",
    "Logstash": "DEVOPS & CI/CD",
    "Fluentd": "DEVOPS & CI/CD",
    "Loki": "DEVOPS & CI/CD",
    "Jaeger": "DEVOPS & CI/CD",
    "OpenTelemetry": "DEVOPS & CI/CD",
    "Splunk": "DEVOPS & CI/CD",
    "PagerDuty": "DEVOPS & CI/CD",
    "Sentry": "DEVOPS & CI/CD",
    "SonarQube": "DEVOPS & CI/CD",
    "Coverity": "DEVOPS & CI/CD",
    "Snyk": "DEVOPS & CI/CD",
    "APM": "DEVOPS & CI/CD",
    "Zabbix": "DEVOPS & CI/CD",
    "Nagios": "DEVOPS & CI/CD",
    "Dockerfile": "DEVOPS & CI/CD",
    "Buildkite": "DEVOPS & CI/CD",
    "FluxCD": "DEVOPS & CI/CD",
    "OpsGenie": "DEVOPS & CI/CD",
    "SaltStack": "DEVOPS & CI/CD",
    "Consul": "DEVOPS & CI/CD",
    "Drone": "DEVOPS & CI/CD",

    # --- OPERATING SYSTEMS & SERVERS ---
    "Linux": "OPERATING SYSTEMS & SERVERS",
    "Ubuntu": "OPERATING SYSTEMS & SERVERS",
    "CentOS": "OPERATING SYSTEMS & SERVERS",
    "Debian": "OPERATING SYSTEMS & SERVERS",
    "Fedora": "OPERATING SYSTEMS & SERVERS",
    "Red Hat": "OPERATING SYSTEMS & SERVERS",
    "RHEL": "OPERATING SYSTEMS & SERVERS",
    "UNIX": "OPERATING SYSTEMS & SERVERS",
    "Windows": "OPERATING SYSTEMS & SERVERS",
    "Windows Server": "OPERATING SYSTEMS & SERVERS",
    "macOS": "OPERATING SYSTEMS & SERVERS",
    "Nginx": "OPERATING SYSTEMS & SERVERS",
    "Apache": "OPERATING SYSTEMS & SERVERS",
    "Tomcat": "OPERATING SYSTEMS & SERVERS",
    "IIS": "OPERATING SYSTEMS & SERVERS",
    "HAProxy": "OPERATING SYSTEMS & SERVERS",
    "WebSphere": "OPERATING SYSTEMS & SERVERS",
    "WebLogic": "OPERATING SYSTEMS & SERVERS",
    "JBoss": "OPERATING SYSTEMS & SERVERS",
    "Gunicorn": "OPERATING SYSTEMS & SERVERS",
    "VMware": "OPERATING SYSTEMS & SERVERS",
    "Virtualization": "OPERATING SYSTEMS & SERVERS",
    "WildFly": "OPERATING SYSTEMS & SERVERS",

    # --- VERSION CONTROL & COLLABORATION ---
    "Git": "VERSION CONTROL & COLLABORATION",
    "GitHub": "VERSION CONTROL & COLLABORATION",
    "GitLab": "VERSION CONTROL & COLLABORATION",
    "Bitbucket": "VERSION CONTROL & COLLABORATION",
    "SVN": "VERSION CONTROL & COLLABORATION",
    "GitFlow": "VERSION CONTROL & COLLABORATION",
    "Subversion": "VERSION CONTROL & COLLABORATION",
    "Mercurial": "VERSION CONTROL & COLLABORATION",
    "Perforce": "VERSION CONTROL & COLLABORATION",
    "Confluence": "VERSION CONTROL & COLLABORATION",
    "Slack": "VERSION CONTROL & COLLABORATION",
    "Microsoft Teams": "VERSION CONTROL & COLLABORATION",
    "Zoom": "VERSION CONTROL & COLLABORATION",

    # --- TESTING & QA ---
    "Selenium": "TESTING & QA",
    "Cypress": "TESTING & QA",
    "Playwright": "TESTING & QA",
    "Puppeteer": "TESTING & QA",
    "Jest": "TESTING & QA",
    "Mocha": "TESTING & QA",
    "Jasmine": "TESTING & QA",
    "Pytest": "TESTING & QA",
    "JUnit": "TESTING & QA",
    "TestNG": "TESTING & QA",
    "NUnit": "TESTING & QA",
    "XUnit": "TESTING & QA",
    "JMeter": "TESTING & QA",
    "Gatling": "TESTING & QA",
    "K6": "TESTING & QA",
    "Locust": "TESTING & QA",
    "LoadRunner": "TESTING & QA",
    "Vitest": "TESTING & QA",
    "RSpec": "TESTING & QA",
    "Postman": "TESTING & QA",
    "Swagger": "TESTING & QA",
    "OpenAPI": "TESTING & QA",
    "REST Assured": "TESTING & QA",
    "Newman": "TESTING & QA",
    "HTTPie": "TESTING & QA",
    "SoapUI": "TESTING & QA",
    "Insomnia": "TESTING & QA",
    "Cucumber": "TESTING & QA",
    "Gherkin": "TESTING & QA",
    "Behave": "TESTING & QA",
    "SpecFlow": "TESTING & QA",
    "Robot Framework": "TESTING & QA",
    "Karate": "TESTING & QA",
    "Appium": "TESTING & QA",
    "WebDriver": "TESTING & QA",
    "WebdriverIO": "TESTING & QA",
    "QA": "TESTING & QA",
    "Test Automation": "TESTING & QA",
    "Manual Testing": "TESTING & QA",
    "TDD": "TESTING & QA",
    "BDD": "TESTING & QA",
    "E2E": "TESTING & QA",
    "Regression Testing": "TESTING & QA",
    "Integration Testing": "TESTING & QA",
    "Load Testing": "TESTING & QA",
    "Stress Testing": "TESTING & QA",
    "Performance Testing": "TESTING & QA",
    "Security Testing": "TESTING & QA",
    "Smoke Testing": "TESTING & QA",
    "Sanity Testing": "TESTING & QA",
    "Pentest": "TESTING & QA",
    "UnitTest": "TESTING & QA",
    "Gradle": "TESTING & QA",
    "Maven": "TESTING & QA",
    "Ant": "TESTING & QA",

    # --- API & PROTOCOLS ---
    "REST": "API & PROTOCOLS",
    "REST API": "API & PROTOCOLS",
    "RESTful": "API & PROTOCOLS",
    "RESTful API": "API & PROTOCOLS",
    "GraphQL": "API & PROTOCOLS",
    "gRPC": "API & PROTOCOLS",
    "SOAP": "API & PROTOCOLS",
    "WebSocket": "API & PROTOCOLS",
    "Socket.IO": "API & PROTOCOLS",
    "HTTP": "API & PROTOCOLS",
    "HTTPS": "API & PROTOCOLS",
    "TCP": "API & PROTOCOLS",
    "UDP": "API & PROTOCOLS",
    "MQTT": "API & PROTOCOLS",
    "AMQP": "API & PROTOCOLS",
    "STOMP": "API & PROTOCOLS",
    "JSON": "API & PROTOCOLS",
    "XML": "API & PROTOCOLS",
    "YAML": "API & PROTOCOLS",
    "Protobuf": "API & PROTOCOLS",
    "Avro": "API & PROTOCOLS",
    "Thrift": "API & PROTOCOLS",
    "API Gateway": "API & PROTOCOLS",
    "RabbitMQ": "API & PROTOCOLS",
    "ActiveMQ": "API & PROTOCOLS",
    "NATS": "API & PROTOCOLS",

    # --- ARCHITECTURE & DESIGN PATTERNS ---
    "Microservices": "ARCHITECTURE & DESIGN PATTERNS",
    "Monolithic": "ARCHITECTURE & DESIGN PATTERNS",
    "SOA": "ARCHITECTURE & DESIGN PATTERNS",
    "MVC": "ARCHITECTURE & DESIGN PATTERNS",
    "MVVM": "ARCHITECTURE & DESIGN PATTERNS",
    "MVP": "ARCHITECTURE & DESIGN PATTERNS",
    "OOP": "ARCHITECTURE & DESIGN PATTERNS",
    "SOLID": "ARCHITECTURE & DESIGN PATTERNS",
    "DRY": "ARCHITECTURE & DESIGN PATTERNS",
    "KISS": "ARCHITECTURE & DESIGN PATTERNS",
    "DDD": "ARCHITECTURE & DESIGN PATTERNS",
    "CQRS": "ARCHITECTURE & DESIGN PATTERNS",
    "Event Sourcing": "ARCHITECTURE & DESIGN PATTERNS",
    "Hexagonal": "ARCHITECTURE & DESIGN PATTERNS",
    "Clean Architecture": "ARCHITECTURE & DESIGN PATTERNS",
    "Design Patterns": "ARCHITECTURE & DESIGN PATTERNS",
    "Singleton": "ARCHITECTURE & DESIGN PATTERNS",
    "Factory": "ARCHITECTURE & DESIGN PATTERNS",
    "Observer Pattern": "ARCHITECTURE & DESIGN PATTERNS",
    "Functional Programming": "ARCHITECTURE & DESIGN PATTERNS",
    "Reactive Programming": "ARCHITECTURE & DESIGN PATTERNS",
    "Async": "ARCHITECTURE & DESIGN PATTERNS",
    "Asynchronous": "ARCHITECTURE & DESIGN PATTERNS",
    "AsyncIO": "ARCHITECTURE & DESIGN PATTERNS",
    "Concurrency": "ARCHITECTURE & DESIGN PATTERNS",
    "Multithreading": "ARCHITECTURE & DESIGN PATTERNS",
    "Parallel Programming": "ARCHITECTURE & DESIGN PATTERNS",
    "SDLC": "ARCHITECTURE & DESIGN PATTERNS",

    # --- PROJECT MANAGEMENT & METHODOLOGIES ---
    "Agile": "PROJECT MANAGEMENT & METHODOLOGIES",
    "Scrum": "PROJECT MANAGEMENT & METHODOLOGIES",
    "Kanban": "PROJECT MANAGEMENT & METHODOLOGIES",
    "Lean": "PROJECT MANAGEMENT & METHODOLOGIES",
    "Waterfall": "PROJECT MANAGEMENT & METHODOLOGIES",
    "SAFe": "PROJECT MANAGEMENT & METHODOLOGIES",
    "Jira": "PROJECT MANAGEMENT & METHODOLOGIES",
    "Confluence": "PROJECT MANAGEMENT & METHODOLOGIES",
    "Trello": "PROJECT MANAGEMENT & METHODOLOGIES",
    "Asana": "PROJECT MANAGEMENT & METHODOLOGIES",
    "Notion": "PROJECT MANAGEMENT & METHODOLOGIES",
    "ClickUp": "PROJECT MANAGEMENT & METHODOLOGIES",
    "Linear": "PROJECT MANAGEMENT & METHODOLOGIES",
    "Miro": "PROJECT MANAGEMENT & METHODOLOGIES",
    "Lucidchart": "PROJECT MANAGEMENT & METHODOLOGIES",
    "Draw.io": "PROJECT MANAGEMENT & METHODOLOGIES",

    # --- DESIGN TOOLS ---
    "Figma": "DESIGN TOOLS",
    "Photoshop": "DESIGN TOOLS",
    "Illustrator": "DESIGN TOOLS",
    "Sketch": "DESIGN TOOLS",
    "InVision": "DESIGN TOOLS",
    "Zeplin": "DESIGN TOOLS",
    "Framer": "DESIGN TOOLS",
    "Canva": "DESIGN TOOLS",
    "UI/UX": "DESIGN TOOLS",
    "UX Design": "DESIGN TOOLS",
    "UI Design": "DESIGN TOOLS",
    "Design System": "DESIGN TOOLS",
    "Wireframing": "DESIGN TOOLS",
    "Prototyping": "DESIGN TOOLS",
    "Unity": "DESIGN TOOLS",
    "Unreal Engine": "DESIGN TOOLS",
    "Cocos": "DESIGN TOOLS",
    "Adobe XD": "DESIGN TOOLS",
    "Principle": "DESIGN TOOLS",
    "UX": "DESIGN TOOLS",
    "UI": "DESIGN TOOLS",

    # --- ARCHITECTURE & DESIGN PATTERNS ---
    "UML": "ARCHITECTURE & DESIGN PATTERNS",
    "WinForms": "ARCHITECTURE & DESIGN PATTERNS",

    # --- SECURITY ---
    "OAuth": "SECURITY",
    "OAuth2": "SECURITY",
    "JWT": "SECURITY",
    "OpenID": "SECURITY",
    "OpenID Connect": "SECURITY",
    "SAML": "SECURITY",
    "LDAP": "SECURITY",
    "SSO": "SECURITY",
    "Keycloak": "SECURITY",
    "Okta": "SECURITY",
    "Auth0": "SECURITY",
    "IAM": "SECURITY",
    "OWASP": "SECURITY",
    "Cybersecurity": "SECURITY",
    "InfoSec": "SECURITY",
    "Information Security": "SECURITY",
    "Network Security": "SECURITY",
    "Application Security": "SECURITY",
    "Cloud Security": "SECURITY",
    "SSL": "SECURITY",
    "TLS": "SECURITY",
    "SSL/TLS": "SECURITY",
    "Encryption": "SECURITY",
    "Cryptography": "SECURITY",
    "Firewall": "SECURITY",
    "WAF": "SECURITY",
    "VPN": "SECURITY",
    "Access Control": "SECURITY",
    "SIEM": "SECURITY",
    "SOC": "SECURITY",
    "SOC 2": "SECURITY",
    "Vulnerability": "SECURITY",
    "GDPR": "SECURITY",
    "PCI DSS": "SECURITY",
    "HIPAA": "SECURITY",
    "ISO 27001": "SECURITY",
    "Burp Suite": "SECURITY",
    "Metasploit": "SECURITY",
    "Wireshark": "SECURITY",
    "Checkmarx": "SECURITY",
    "Fortify": "SECURITY",
    "Threat Modeling": "SECURITY",
}


# ============================================================
#  NOISE_BLOCKLIST: words that look like skills but are not.
#  These are filtered out during normalization.
# ============================================================
NOISE_BLOCKLIST: set[str] = {
    "affinity", "emotion", "shortcut", "render",
}


# ============================================================
#  SYNONYM_MAP: variant_lower → canonical_name
#  Every possible variation maps to the canonical form above.
# ============================================================
SYNONYM_MAP: dict[str, str] = {}


def _build_synonym_map() -> dict[str, str]:
    """Build the full synonym map from canonical names + explicit aliases."""

    # Start with identity mapping: every canonical name maps to itself (lowercased key)
    smap: dict[str, str] = {}
    for canonical in SKILL_CATEGORY_MAP:
        smap[canonical.lower()] = canonical

    # Explicit aliases — variant_lower → canonical_name
    aliases: dict[str, str] = {
        # --- Programming Languages ---
        "python3": "Python", "python2": "Python",
        "java8": "Java", "java11": "Java", "java17": "Java", "java21": "Java",
        "golang": "Go",
        "c/c++": "C/C++",
        "objective-c": "Objective-C", "objectivec": "Objective-C",
        "matlab": "Matlab",
        "plsql": "PL/SQL", "pl/sql": "PL/SQL",

        # --- Frontend basics ---
        "html 5": "HTML5", "html5": "HTML5",
        "css 3": "CSS3", "css3": "CSS3",
        "tailwind": "Tailwind CSS", "tailwindcss": "Tailwind CSS", "tailwind css": "Tailwind CSS",
        "bootstrap": "Bootstrap", "sass": "SASS", "scss": "SCSS",

        # --- Frontend Frameworks ---
        "reactjs": "React", "react.js": "React",
        "vuejs": "Vue", "vue.js": "Vue", "vue2": "Vue", "vue3": "Vue",
        "angularjs": "Angular", "angular.js": "Angular",
        "angular2": "Angular", "angular4": "Angular", "angular8": "Angular",
        "angular12": "Angular", "angular14": "Angular", "angular16": "Angular",
        "nextjs": "Next.js", "next.js": "Next.js",
        "nuxtjs": "Nuxt.js", "nuxt": "Nuxt.js",
        "jquery": "jQuery",
        "backbone.js": "Backbone.js", "backbone": "Backbone.js",
        "material-ui": "Material UI", "material ui": "Material UI",
        "ant design": "Ant Design", "antd": "Ant Design",
        "styled-components": "Styled Components",
        "react router": "React Router", "react query": "React Query",
        "npm": "NPM", "yarn": "Yarn", "parcel": "Parcel",
        "babel": "Babel",
        "esbuild": "esbuild", "esbuild": "esbuild",
        "chakra ui": "Chakra UI", "chakra-ui": "Chakra UI",
        "htmx": "HTMX",

        # --- Backend ---
        "node.js": "Node.js", "nodejs": "Node.js",
        "express.js": "Express", "expressjs": "Express",
        "nest.js": "NestJS", "nestjs": "NestJS",
        ".net": ".NET", "dotnet": ".NET",
        ".net core": ".NET Core", "dotnet core": ".NET Core",
        "asp.net": "ASP.NET",
        "asp.net core": "ASP.NET Core",
        "ef core": "EF Core", "entity framework": "Entity Framework",
        "ruby on rails": "Ruby on Rails", "rails": "Ruby on Rails",
        "spring boot": "Spring Boot", "springboot": "Spring Boot",
        "spring framework": "Spring", "spring": "Spring",
        "spring mvc": "Spring MVC", "spring cloud": "Spring Cloud",
        "spring security": "Spring Security", "spring data": "Spring Data",
        "wordpress": "WordPress", "magento": "Magento",
        "cakephp": "CakePHP", "codeigniter": "CodeIgniter",
        "sqlalchemy": "SQLAlchemy",

        # --- Mobile ---
        "react native": "React Native",
        "swiftui": "SwiftUI", "swift ui": "SwiftUI",
        "jetpack compose": "Jetpack Compose",
        "kotlin multiplatform": "Kotlin Multiplatform", "kmm": "KMM",
        "android studio": "Android Studio",
        "android sdk": "Android SDK", "ios sdk": "iOS SDK",
        "mobile app": "Mobile App", "mobile app": "Mobile App",
        "progressive web app": "Progressive Web App", "pwa": "PWA",
        "cordova": "Cordova",
        "xamarin": "Xamarin",
        "maui": "MAUI", ".net maui": "MAUI",
        "kmp": "KMP",

        # --- Databases ---
        "postgresql": "PostgreSQL", "postgres": "PostgreSQL", "postgresgl": "PostgreSQL",
        "mongodb": "MongoDB", "mysql": "MySQL",
        "mariadb": "MariaDB", "sqlite": "SQLite",
        "ms sql": "MS SQL Server", "mssql": "MS SQL Server", "sql server": "MS SQL Server",
        "ms sql server": "MS SQL Server",
        "oracle": "Oracle", "oracle db": "Oracle DB",
        "dynamodb": "DynamoDB",
        "elasticsearch": "Elasticsearch", "elastic search": "Elasticsearch",
        "hbase": "HBase",
        "neo4j": "Neo4j",
        "cockroachdb": "CockroachDB",
        "cosmosdb": "CosmosDB", "cosmos db": "CosmosDB",
        "couchbase": "CouchBase",
        "clickhouse": "ClickHouse",
        "elasticache": "ElastiCache",
        "firestore": "Firestore", "firebase": "Firebase",
        "nosql": "NoSQL",
        "memcached": "Memcached",
        "db2": "DB2", "teradata": "Teradata", "vertica": "Vertica",

        # --- Cloud ---
        "aws": "AWS", "amazon web services": "AWS",
        "gcp": "GCP", "google cloud": "GCP", "google cloud platform": "GCP",
        "azure": "Azure", "microsoft azure": "Azure",
        "ibm cloud": "IBM Cloud",
        "digitalocean": "DigitalOcean",
        "ec2": "EC2", "s3": "S3", "rds": "RDS",
        "lambda": "Lambda", "aws lambda": "AWS Lambda",
        "ecs": "ECS", "eks": "EKS", "fargate": "Fargate",
        "cloudwatch": "CloudWatch",
        "sns": "SNS", "sqs": "SQS", "kinesis": "Kinesis",
        "step functions": "Step Functions",
        "cognito": "Cognito",
        "cloudformation": "CloudFormation",
        "aws cdk": "AWS CDK", "aws sam": "AWS SAM",
        "cloud sql": "Cloud SQL", "cloud functions": "Cloud Functions",
        "cloud storage": "Cloud Storage",
        "gke": "GKE", "aks": "AKS",
        "azure blob": "Azure Blob", "azure functions": "Azure Functions",
        "azure pipelines": "Azure Pipelines",
        "azure devops": "Azure DevOps",
        "serverless": "Serverless", "serverless framework": "Serverless Framework",
        "faas": "FaaS",
        "pub/sub": "Pub/Sub", "pubsub": "Pub/Sub",
        "alibaba cloud": "Alibaba Cloud", "aliyun": "Alibaba Cloud",
        "cloud run": "Cloud Run",
        "heroku": "Heroku",
        "linode": "Linode",
        "oracle cloud": "Oracle Cloud",
        "cdk": "AWS CDK",

        # --- DevOps ---
        "docker": "Docker", "docker compose": "Docker Compose",
        "docker-compose": "Docker Compose",
        "docker swarm": "Docker Swarm",
        "kubernetes": "Kubernetes", "k8s": "Kubernetes",
        "ci/cd": "CI/CD", "cicd": "CI/CD",
        "github actions": "GitHub Actions",
        "gitlab ci": "GitLab CI", "gitlab ci/cd": "GitLab CI",
        "circle ci": "CircleCI", "circleci": "CircleCI",
        "argo cd": "ArgoCD", "argocd": "ArgoCD",
        "travis ci": "Travis CI", "travisci": "Travis CI",
        "jenkins": "Jenkins",
        "terraform": "Terraform", "ansible": "Ansible",
        "devops": "DevOps", "devsecops": "DevSecOps",
        "sre": "SRE", "site reliability": "SRE",
        "elk stack": "ELK Stack", "elk": "ELK Stack",
        "new relic": "New Relic", "newrelic": "New Relic",
        "sonarqube": "SonarQube", "sonar": "SonarQube",
        "teamcity": "TeamCity",
        "opentelemetry": "OpenTelemetry",
        "datadog": "Datadog",
        "dockerfile": "Dockerfile",
        "buildkite": "Buildkite",
        "fluxcd": "FluxCD", "flux cd": "FluxCD",
        "opsgenie": "OpsGenie",
        "saltstack": "SaltStack", "salt": "SaltStack",
        "consul": "Consul",
        "drone": "Drone",

        # --- OS & Servers ---
        "linux": "Linux", "ubuntu": "Ubuntu",
        "centos": "CentOS", "debian": "Debian", "fedora": "Fedora",
        "red hat": "Red Hat", "redhat": "Red Hat", "rhel": "RHEL",
        "unix": "UNIX",
        "windows": "Windows", "windows server": "Windows Server",
        "macos": "macOS",
        "nginx": "Nginx",
        "apache": "Apache", "apache http": "Apache",
        "tomcat": "Tomcat", "apache tomcat": "Tomcat",
        "iis": "IIS",
        "haproxy": "HAProxy",
        "websphere": "WebSphere", "weblogic": "WebLogic",
        "jboss": "JBoss",
        "openshift": "OpenShift",

        # --- Version Control ---
        "git": "Git",
        "github": "GitHub",
        "gitlab": "GitLab",
        "bitbucket": "Bitbucket",
        "svn": "SVN", "subversion": "SVN",
        "gitflow": "GitFlow",

        # --- Testing ---
        "selenium": "Selenium", "cypress": "Cypress",
        "playwright": "Playwright", "puppeteer": "Puppeteer",
        "jest": "Jest", "mocha": "Mocha", "jasmine": "Jasmine",
        "pytest": "Pytest",
        "junit": "JUnit", "testng": "TestNG",
        "nunit": "NUnit", "xunit": "XUnit",
        "jmeter": "JMeter",
        "gatling": "Gatling", "k6": "K6",
        "locust": "Locust", "loadrunner": "LoadRunner",
        "postman": "Postman",
        "swagger": "Swagger", "openapi": "OpenAPI",
        "rest assured": "REST Assured",
        "newman": "Newman", "httpie": "HTTPie",
        "soapui": "SoapUI", "insomnia": "Insomnia",
        "cucumber": "Cucumber", "gherkin": "Gherkin",
        "behave": "Behave", "specflow": "SpecFlow",
        "robot framework": "Robot Framework",
        "karate": "Karate",
        "appium": "Appium",
        "webdriver": "WebDriver", "webdriverio": "WebdriverIO",
        "qa": "QA", "quality assurance": "QA",
        "test automation": "Test Automation",
        "manual testing": "Manual Testing",
        "tdd": "TDD", "bdd": "BDD",
        "e2e": "E2E", "end-to-end": "E2E",
        "regression testing": "Regression Testing",
        "integration testing": "Integration Testing",
        "load testing": "Load Testing",
        "stress testing": "Stress Testing",
        "performance testing": "Performance Testing",
        "security testing": "Security Testing",
        "smoke testing": "Smoke Testing",
        "sanity testing": "Sanity Testing",
        "pentest": "Pentest", "penetration testing": "Pentest",
        "pen testing": "Pentest",
        "unittest": "UnitTest",
        "gradle": "Gradle", "maven": "Maven", "ant": "Ant",

        # --- API & Protocols ---
        "rest": "REST",
        "rest api": "REST API",
        "restful": "RESTful", "restful api": "RESTful API",
        "graphql": "GraphQL",
        "grpc": "gRPC",
        "soap": "SOAP",
        "websocket": "WebSocket", "websockets": "WebSocket",
        "socket.io": "Socket.IO",
        "http": "HTTP", "https": "HTTPS",
        "tcp": "TCP", "udp": "UDP",
        "mqtt": "MQTT", "amqp": "AMQP",
        "json": "JSON", "xml": "XML", "yaml": "YAML",
        "protobuf": "Protobuf", "avro": "Avro", "thrift": "Thrift",
        "api gateway": "API Gateway",
        "rabbitmq": "RabbitMQ", "rabbit mq": "RabbitMQ",
        "activemq": "ActiveMQ", "active mq": "ActiveMQ",
        "nats": "NATS",

        # --- Architecture ---
        "microservices": "Microservices", "microservice": "Microservices",
        "monolithic": "Monolithic", "monolith": "Monolithic",
        "soa": "SOA",
        "mvc": "MVC", "mvvm": "MVVM", "mvp": "MVP",
        "oop": "OOP", "object oriented": "OOP",
        "solid": "SOLID",
        "dry": "DRY", "kiss": "KISS",
        "ddd": "DDD", "domain driven design": "DDD",
        "cqrs": "CQRS",
        "event sourcing": "Event Sourcing",
        "event-driven": "Event Sourcing",
        "hexagonal": "Hexagonal",
        "clean architecture": "Clean Architecture",
        "design patterns": "Design Patterns",
        "singleton": "Singleton", "factory": "Factory",
        "observer": "Observer Pattern", "observer pattern": "Observer Pattern",
        "functional programming": "Functional Programming",
        "reactive programming": "Reactive Programming",
        "async": "Async", "asynchronous": "Asynchronous",
        "asyncio": "AsyncIO",
        "concurrency": "Concurrency",
        "multithreading": "Multithreading",
        "parallel programming": "Parallel Programming",
        "sdlc": "SDLC",

        # --- PM & Methodologies ---
        "agile": "Agile", "scrum": "Scrum",
        "kanban": "Kanban",
        "lean": "Lean",
        "waterfall": "Waterfall",
        "safe": "SAFe",
        "jira": "Jira",
        "trello": "Trello", "asana": "Asana",
        "notion": "Notion",
        "clickup": "ClickUp",
        "linear": "Linear",
        "miro": "Miro",
        "lucidchart": "Lucidchart",
        "draw.io": "Draw.io",

        # --- Design ---
        "figma": "Figma",
        "photoshop": "Photoshop", "adobe photoshop": "Photoshop",
        "illustrator": "Illustrator", "adobe illustrator": "Illustrator",
        "sketch": "Sketch",
        "invision": "InVision",
        "zeplin": "Zeplin", "framer": "Framer",
        "canva": "Canva",
        "ui/ux": "UI/UX", "ui / ux": "UI/UX",
        "ux design": "UX Design", "ui design": "UI Design",
        "design system": "Design System",
        "wireframing": "Wireframing", "prototyping": "Prototyping",
        "unity": "Unity", "unreal engine": "Unreal Engine",
        "cocos": "Cocos", "cocos2d": "Cocos",
        "adobe xd": "Adobe XD",
        "principle": "Principle",

        # --- Data Engineering ---
        "spark": "Spark", "apache spark": "Spark",
        "pyspark": "PySpark",
        "hadoop": "Hadoop",
        "kafka": "Kafka", "apache kafka": "Kafka",
        "airflow": "Airflow", "apache airflow": "Airflow",
        "flink": "Flink", "apache flink": "Flink",
        "pandas": "Pandas", "numpy": "NumPy",
        "matplotlib": "Matplotlib", "seaborn": "Seaborn",
        "plotly": "Plotly", "scipy": "SciPy",
        "hive": "Hive", "presto": "Presto", "trino": "Trino",
        "impala": "Impala",
        "databricks": "Databricks",
        "snowflake": "Snowflake",
        "bigquery": "BigQuery", "big query": "BigQuery",
        "redshift": "Redshift",
        "data warehouse": "Data Warehouse",
        "data lake": "Data Lake", "data mesh": "Data Mesh",
        "delta lake": "Delta Lake", "lakehouse": "Lakehouse",
        "data pipeline": "Data Pipeline",
        "etl": "ETL", "elt": "ELT",
        "dbt": "DBT",
        "informatica": "Informatica", "talend": "Talend",
        "nifi": "NiFi", "apache nifi": "NiFi",
        "pentaho": "Pentaho",
        "aws glue": "AWS Glue", "glue": "Glue",
        "azure data factory": "Azure Data Factory",
        "emr": "EMR",
        "airbyte": "Airbyte", "fivetran": "Fivetran",
        "luigi": "Luigi", "dagster": "Dagster", "prefect": "Prefect",
        "apache beam": "Apache Beam",
        "apache storm": "Apache Storm", "storm": "Apache Storm",
        "dataflow": "Dataflow", "dataproc": "Dataproc",
        "power bi": "Power BI", "powerbi": "Power BI",
        "tableau": "Tableau",
        "looker": "Looker",
        "metabase": "Metabase",
        "superset": "Superset", "apache superset": "Superset",
        "redash": "Redash",
        "qlik": "Qlik", "qlikview": "QlikView",
        "google sheets": "Google Sheets",
        "excel": "Excel",
        "mode": "Mode",
        "athena": "Athena",
        "azure synapse": "Azure Synapse", "synapse": "Synapse",

        # --- ML/AI ---
        "tensorflow": "TensorFlow",
        "pytorch": "PyTorch",
        "keras": "Keras",
        "scikit-learn": "Scikit-learn", "sklearn": "Scikit-learn",
        "xgboost": "XGBoost",
        "lightgbm": "LightGBM",
        "catboost": "CatBoost",
        "hugging face": "Hugging Face", "huggingface": "Hugging Face",
        "llm": "LLM", "large language model": "LLM",
        "gpt": "GPT",
        "openai": "OpenAI", "chatgpt": "ChatGPT",
        "langchain": "LangChain",
        "rag": "RAG",
        "mlflow": "MLflow",
        "mlops": "MLOps",
        "kubeflow": "Kubeflow",
        "sagemaker": "SageMaker",
        "azure ml": "Azure ML",
        "azure machine learning": "Azure Machine Learning",
        "vertex ai": "Vertex AI",
        "computer vision": "Computer Vision",
        "image processing": "Image Processing",
        "bert": "BERT",
        "transformers": "Transformers",
        "onnx": "ONNX",
        "tensorrt": "TensorRT",
        "triton": "Triton",
        "spacy": "SpaCy",
        "nltk": "NLTK",
        "ray": "Ray", "jax": "JAX", "mxnet": "Mxnet",
        "google colab": "Google Colab",
        "jupyter": "Jupyter", "jupyter notebook": "Jupyter Notebook",
        "dvc": "DVC",
        "detectron": "Detectron",
        "opencv": "OpenCV",
        "yolo": "YOLO",
        "neptune": "Neptune",
        "faiss": "FAISS",
        "milvus": "Milvus", "pinecone": "Pinecone",
        "weaviate": "Weaviate", "chroma": "Chroma",
        "vector database": "Vector Database",
        "ai": "AI", "artificial intelligence": "AI",
        "ml": "ML", "machine learning": "Machine Learning",
        "deep learning": "Deep Learning",
        "nlp": "NLP", "natural language processing": "NLP",
        "wandb": "Weights & Biases", "weights and biases": "Weights & Biases",

        # --- Security ---
        "oauth": "OAuth", "oauth2": "OAuth2", "oauth 2.0": "OAuth2",
        "jwt": "JWT",
        "openid": "OpenID", "openid connect": "OpenID Connect",
        "saml": "SAML", "ldap": "LDAP",
        "sso": "SSO", "single sign-on": "SSO",
        "keycloak": "Keycloak", "okta": "Okta",
        "iam": "IAM", "identity management": "IAM",
        "owasp": "OWASP",
        "cybersecurity": "Cybersecurity", "cyber security": "Cybersecurity",
        "infosec": "InfoSec",
        "information security": "Information Security",
        "network security": "Network Security",
        "application security": "Application Security",
        "cloud security": "Cloud Security",
        "ssl": "SSL", "tls": "TLS", "ssl/tls": "SSL/TLS",
        "encryption": "Encryption", "cryptography": "Cryptography",
        "firewall": "Firewall", "waf": "WAF", "vpn": "VPN",
        "access control": "Access Control",
        "siem": "SIEM", "soc": "SOC", "soc2": "SOC 2", "soc 2": "SOC 2",
        "vulnerability": "Vulnerability",
        "gdpr": "GDPR", "pci dss": "PCI DSS",
        "hipaa": "HIPAA", "iso 27001": "ISO 27001",
        "burp suite": "Burp Suite",
        "metasploit": "Metasploit",
        "wireshark": "Wireshark",
        "checkmarx": "Checkmarx",
        "fortify": "Fortify",
        "threat modeling": "Threat Modeling",

        # --- New languages ---
        "elixir": "Elixir", "haskell": "Haskell", "lua": "Lua",

        # --- New backend ---
        "aiohttp": "aiohttp",

        # --- New frontend ---
        "foundation": "Foundation",
        "pnpm": "pnpm",

        # --- New testing ---
        "vitest": "Vitest",
        "rspec": "RSpec",

        # --- New version control ---
        "mercurial": "Mercurial", "hg": "Mercurial",
        "perforce": "Perforce", "p4": "Perforce",

        # --- New cloud ---
        "netlify": "Netlify",

        # --- New security ---
        "auth0": "Auth0",

        # --- New API ---
        "stomp": "STOMP",

        # --- New cloud ---
        "azure service bus": "Azure Service Bus",

        # --- New mobile ---
        "native app": "Mobile App",
        "httpd": "Apache",

        # --- New OS/Servers ---
        "vmware": "VMware", "vsphere": "VMware",
        "virtualization": "Virtualization",
        "wildfly": "WildFly",

        # --- New Design ---
        "ux": "UX", "ui": "UI",
        "ui-ux": "UI/UX", "ux/ui": "UI/UX",

        # --- New Architecture ---
        "uml": "UML", "uml/bpmn": "UML",
        "winforms": "WinForms",

        # --- New Testing ---
        "unit test": "UnitTest",
        "usability testing": "Usability Testing",
    }

    smap.update(aliases)
    return smap


# Build once at module load
SYNONYM_MAP = _build_synonym_map()


class SkillNormalizer:
    """
    Centralized skill normalizer.

    Usage:
        normalizer = SkillNormalizer()
        canonical = normalizer.normalize("reactjs")  # → "React"
        category = normalizer.get_category("React")  # → "FRONTEND FRAMEWORKS & LIBRARIES"
    """

    def __init__(self, log_dir: Optional[str] = None):
        self._synonym_map = SYNONYM_MAP
        self._category_map = SKILL_CATEGORY_MAP
        self._blocklist = NOISE_BLOCKLIST
        self._unmapped_counter: Counter = Counter()
        self._log_dir = log_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs'
        )

    def normalize(self, skill_text: str) -> Optional[str]:
        """
        Normalize a skill name to its canonical form.

        :param skill_text: Raw skill text (e.g., "reactjs", ".Net", "Amazon Web Services")
        :return: Canonical name (e.g., "React", ".NET", "AWS") or None if unknown/noise
        """
        if not skill_text or not isinstance(skill_text, str):
            return None

        key = skill_text.lower().strip()
        if not key:
            return None

        # Block noise words (ambiguous common English words)
        if key in self._blocklist:
            return None

        # Direct lookup
        if key in self._synonym_map:
            return self._synonym_map[key]

        # Fallback: try without spaces to handle Spacy multi-token patterns
        # e.g. "Java 8" → "java8", "Angular 12" → "angular12", "Vue 2" → "vue2"
        compact_key = key.replace(" ", "")
        if compact_key != key and compact_key in self._synonym_map:
            return self._synonym_map[compact_key]

        # Track unmapped skill frequency (silent — no per-call log spam)
        self._unmapped_counter[skill_text.strip()] += 1
        return None

    def get_category(self, canonical_name: str) -> Optional[str]:
        """
        Get the category of a canonical skill name.

        :param canonical_name: Canonical skill name (from normalize())
        :return: Category string or None
        """
        return self._category_map.get(canonical_name)

    def normalize_with_category(self, skill_text: str) -> tuple[Optional[str], Optional[str]]:
        """
        Normalize and get category in one call.

        :return: (canonical_name, category) tuple
        """
        canonical = self.normalize(skill_text)
        if not canonical:
            return None, None
        return canonical, self.get_category(canonical)

    def normalize_list(self, skills: list[str]) -> list[str]:
        """
        Normalize a list of skills, removing duplicates and unknowns.

        For combo skills like "Agile/Scrum" or "AWS/GCP", if the full
        string has no exact match, split on '/' and normalize each part
        individually.

        :param skills: List of raw skill names
        :return: Deduplicated list of canonical skill names
        """
        seen: set[str] = set()
        result: list[str] = []
        for skill in skills:
            canonical = self.normalize(skill)
            if canonical and canonical not in seen:
                seen.add(canonical)
                result.append(canonical)
            elif canonical is None and '/' in skill:
                # Combo split fallback: "Agile/Scrum" → ["Agile", "Scrum"]
                parts = [p.strip() for p in skill.split('/')]
                for part in parts:
                    if part:
                        c = self.normalize(part)
                        if c and c not in seen:
                            seen.add(c)
                            result.append(c)
        return result

    def flush_unmapped_log(self, threshold: int = 1) -> str | None:
        """
        Write unmapped skills frequency report to a separate log file.

        Call this at spider close or end of pipeline run to dump
        accumulated unmapped skills without polluting the main logs.

        :param threshold: Only log skills with count >= threshold
        :return: Path to log file, or None if nothing to log
        """
        if not self._unmapped_counter:
            return None

        os.makedirs(self._log_dir, exist_ok=True)
        log_path = os.path.join(self._log_dir, 'unmapped_skills.log')

        # Filter by threshold and sort by frequency desc
        filtered = [
            (skill, count)
            for skill, count in self._unmapped_counter.most_common()
            if count >= threshold
        ]

        if not filtered:
            return None

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Unmapped Skills Report — {timestamp}\n")
            f.write(f"Total unique unmapped: {len(filtered)}\n")
            f.write(f"Threshold: >= {threshold} occurrences\n")
            f.write(f"{'='*60}\n")
            for skill, count in filtered:
                marker = ' ⚠️ TRENDING' if count >= 50 else ''
                f.write(f"  {count:>5}x  {skill}{marker}\n")
            f.write(f"{'='*60}\n")

        # Also log summary to main logger
        total = sum(c for _, c in filtered)
        trending = [s for s, c in filtered if c >= 50]
        logger.info(
            f"Unmapped skills report: {len(filtered)} unique terms, "
            f"{total} total occurrences → {log_path}"
        )
        if trending:
            logger.warning(
                f"🔔 TRENDING unmapped skills (>=50 hits): {trending} "
                f"— consider adding to SKILL_CATEGORY_MAP"
            )

        # Reset counter after flushing
        self._unmapped_counter.clear()
        return log_path

    def get_unmapped_stats(self) -> dict[str, int]:
        """
        Get current unmapped skills counter (for inspection/testing).

        :return: Dict of skill_text → count
        """
        return dict(self._unmapped_counter.most_common())
