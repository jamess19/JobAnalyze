"""
Skill Extractor - NLP-based extraction using Spacy
Extracts technical skills and business domains from job descriptions

All patterns use [{"LOWER": "..."}] format for case-insensitive matching.
"""

import spacy
from spacy.matcher import Matcher
from spacy.tokens import Doc
from typing import Dict, List, Set
import logging

logger = logging.getLogger(__name__)


class SkillExtractor:
    """
    Extract technical skills and business domains from text using Spacy NLP.
    
    Uses EntityRuler for pattern matching and custom logic for skill normalization.
    """
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initialize Spacy model with custom entity ruler
        
        :param model_name: Spacy model to load (default: en_core_web_sm)
        """
        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"Loaded Spacy model: {model_name}")
        except OSError:
            logger.warning(f"Model {model_name} not found. Downloading...")
            spacy.cli.download(model_name)
            self.nlp = spacy.load(model_name)
        
        # Add custom entity ruler for skills and domains
        self._add_entity_patterns()
        
        # Add custom matcher for complex patterns
        self.matcher = Matcher(self.nlp.vocab)
        self._add_matcher_patterns()
    
    def _add_entity_patterns(self):
        """Add EntityRuler with predefined skill and domain patterns"""
        
        # Create entity ruler and add to pipeline before NER
        ruler = self.nlp.add_pipe("entity_ruler", before="ner")
        
        patterns = [
            # ============================================================
            #                    PROGRAMMING LANGUAGES
            # ============================================================
            {"label": "SKILL", "pattern": [{"LOWER": "python"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "java"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "javascript"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "typescript"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "c++"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "c#"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "c/c++"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "c"}, {"TEXT": "/"}, {"LOWER": "c++"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "golang"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "go"}], "id": "golang"},
            {"label": "SKILL", "pattern": [{"LOWER": "rust"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ruby"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "php"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "swift"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "kotlin"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "scala"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "perl"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "shell"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "bash"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "powershell"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "objective-c"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "objectivec"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "dart"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "r"}], "id": "r_lang"},
            {"label": "SKILL", "pattern": [{"LOWER": "lua"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "groovy"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cobol"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "fortran"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "assembly"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "haskell"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "elixir"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "erlang"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "clojure"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "f#"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "matlab"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vba"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "apache"}, {"LOWER": "groovy"}]},
            # Versioned languages
            {"label": "SKILL", "pattern": [{"LOWER": "java8"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "java11"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "java17"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "java"}, {"TEXT": {"REGEX": "^(8|11|17|21)$"}}]},
            {"label": "SKILL", "pattern": [{"LOWER": "python3"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "python2"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "python"}, {"TEXT": {"REGEX": "^[23](\\.\\d+)?$"}}]},
            
            # ============================================================
            #                 FRONTEND - HTML/CSS/JS BASICS
            # ============================================================
            {"label": "SKILL", "pattern": [{"LOWER": "html"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "html5"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "html"}, {"TEXT": "5"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "css"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "css3"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "css"}, {"TEXT": "3"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sass"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "scss"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "stylus"}]},
            
            # ============================================================
            #                  FRONTEND FRAMEWORKS & LIBRARIES
            # ============================================================
            # React ecosystem
            {"label": "SKILL", "pattern": [{"LOWER": "react"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "reactjs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "react.js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "react"}, {"LOWER": "."}, {"LOWER": "js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "react"}, {"LOWER": "native"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "redux"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "react"}, {"LOWER": "query"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "react"}, {"LOWER": "router"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "next.js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "nextjs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "next"}, {"LOWER": "."}, {"LOWER": "js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gatsby"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "remix"}]},
            # Angular ecosystem
            {"label": "SKILL", "pattern": [{"LOWER": "angular"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "angularjs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "angular.js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "angular"}, {"TEXT": {"REGEX": "^\\d+$"}}]},
            {"label": "SKILL", "pattern": [{"LOWER": "angular2"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "angular4"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "angular8"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "angular12"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "angular14"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "angular16"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "rxjs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ngrx"}]},
            # Vue ecosystem
            {"label": "SKILL", "pattern": [{"LOWER": "vue"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vuejs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vue.js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vue"}, {"LOWER": "."}, {"LOWER": "js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vue2"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vue3"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vue"}, {"TEXT": {"REGEX": "^[23]$"}}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vuex"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pinia"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "nuxt.js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "nuxtjs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "nuxt"}]},
            # Other frontend frameworks
            {"label": "SKILL", "pattern": [{"LOWER": "svelte"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sveltekit"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ember"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ember.js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "backbone"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "backbone.js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "jquery"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "alpinejs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "alpine.js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "htmx"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "solid.js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "solidjs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "preact"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "lit"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "lit-element"}]},
            # CSS Frameworks
            {"label": "SKILL", "pattern": [{"LOWER": "tailwind"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "tailwindcss"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "tailwind"}, {"LOWER": "css"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "bootstrap"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "bulma"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "foundation"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "material"}, {"LOWER": "ui"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "material-ui"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mui"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "antd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ant"}, {"LOWER": "design"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "chakra"}, {"LOWER": "ui"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "styled-components"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "emotion"}]},
            # Build tools
            {"label": "SKILL", "pattern": [{"LOWER": "webpack"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vite"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "babel"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "rollup"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "parcel"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "esbuild"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gulp"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "grunt"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "npm"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "yarn"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pnpm"}]},
            
            # ============================================================
            #                  BACKEND FRAMEWORKS & LIBRARIES
            # ============================================================
            # Node.js ecosystem
            {"label": "SKILL", "pattern": [{"LOWER": "node.js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "nodejs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "node"}, {"LOWER": "."}, {"LOWER": "js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "express"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "express.js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "expressjs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "nestjs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "nest.js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "nest"}, {"LOWER": "."}, {"LOWER": "js"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "koa"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "hapi"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "fastify"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "adonis"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "adonisjs"}]},
            # Python ecosystem
            {"label": "SKILL", "pattern": [{"LOWER": "django"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "flask"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "fastapi"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "tornado"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "aiohttp"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "celery"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sqlalchemy"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "asyncio"}]},
            # Java ecosystem
            {"label": "SKILL", "pattern": [{"LOWER": "spring"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "spring"}, {"LOWER": "boot"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "springboot"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "spring"}, {"LOWER": "framework"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "spring"}, {"LOWER": "mvc"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "spring"}, {"LOWER": "cloud"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "spring"}, {"LOWER": "security"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "spring"}, {"LOWER": "data"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "hibernate"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "jpa"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "struts"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "jsf"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "quarkus"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "micronaut"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "maven"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gradle"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ant"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "jboss"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "wildfly"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "weblogic"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "websphere"}]},
            # .NET ecosystem
            {"label": "SKILL", "pattern": [{"LOWER": ".net"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "dotnet"}]},
            {"label": "SKILL", "pattern": [{"LOWER": ".net"}, {"LOWER": "core"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "dotnet"}, {"LOWER": "core"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "asp.net"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "asp.net"}, {"LOWER": "core"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "entity"}, {"LOWER": "framework"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ef"}, {"LOWER": "core"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "blazor"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "xamarin"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "maui"}]},
            # PHP ecosystem
            {"label": "SKILL", "pattern": [{"LOWER": "laravel"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "symfony"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "codeigniter"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "yii"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cakephp"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "zend"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "drupal"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "wordpress"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "magento"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "prestashop"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "composer"}]},
            # Ruby ecosystem
            {"label": "SKILL", "pattern": [{"LOWER": "rails"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ruby"}, {"LOWER": "on"}, {"LOWER": "rails"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sinatra"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "hanami"}]},
            # Go ecosystem
            {"label": "SKILL", "pattern": [{"LOWER": "gin"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "echo"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "fiber"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "beego"}]},
            
            # ============================================================
            #                    MOBILE DEVELOPMENT
            # ============================================================
            {"label": "SKILL", "pattern": [{"LOWER": "flutter"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "react"}, {"LOWER": "native"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "swiftui"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "swift"}, {"LOWER": "ui"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "kotlin"}, {"LOWER": "multiplatform"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "kmp"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "kmm"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ionic"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cordova"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "phonegap"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "capacitor"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "expo"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "android"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "android"}, {"LOWER": "sdk"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ios"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ios"}, {"LOWER": "sdk"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "xcode"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "android"}, {"LOWER": "studio"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "uikit"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "jetpack"}, {"LOWER": "compose"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "native"}, {"LOWER": "app"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mobile"}, {"LOWER": "app"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pwa"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "progressive"}, {"LOWER": "web"}, {"LOWER": "app"}]},
            
            # ============================================================
            #                        DATABASES
            # ============================================================
            # SQL Databases
            {"label": "SKILL", "pattern": [{"LOWER": "sql"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mysql"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "postgresql"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "postgres"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mariadb"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sqlite"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "oracle"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "oracle"}, {"LOWER": "db"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ms"}, {"LOWER": "sql"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mssql"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sql"}, {"LOWER": "server"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "t-sql"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pl/sql"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pl"}, {"TEXT": "/"}, {"LOWER": "sql"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "plsql"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "db2"}]},
            # NoSQL Databases
            {"label": "SKILL", "pattern": [{"LOWER": "nosql"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mongodb"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "redis"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "elasticsearch"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "elastic"}, {"LOWER": "search"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "dynamodb"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cassandra"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "couchdb"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "couchbase"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "neo4j"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "arangodb"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "hbase"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "memcached"}]},
            # Cloud Databases
            {"label": "SKILL", "pattern": [{"LOWER": "firebase"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "firestore"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "supabase"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "planetscale"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cockroachdb"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "tidb"}]},
            # Data Warehouses
            {"label": "SKILL", "pattern": [{"LOWER": "snowflake"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "bigquery"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "big"}, {"LOWER": "query"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "redshift"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "synapse"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "azure"}, {"LOWER": "synapse"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "clickhouse"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vertica"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "teradata"}]},
            
            # ============================================================
            #                   DATA ENGINEERING & ANALYTICS
            # ============================================================
            # Big Data Processing
            {"label": "SKILL", "pattern": [{"LOWER": "spark"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "apache"}, {"LOWER": "spark"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pyspark"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "hadoop"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "hive"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "presto"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "trino"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "impala"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "flink"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "apache"}, {"LOWER": "flink"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "storm"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "apache"}, {"LOWER": "storm"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "beam"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "apache"}, {"LOWER": "beam"}]},
            # Message Queues & Streaming
            {"label": "SKILL", "pattern": [{"LOWER": "kafka"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "apache"}, {"LOWER": "kafka"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "rabbitmq"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "rabbit"}, {"LOWER": "mq"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "activemq"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "active"}, {"LOWER": "mq"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "amazon"}, {"LOWER": "sqs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sqs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sns"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pubsub"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pub/sub"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pub"}, {"TEXT": "/"}, {"LOWER": "sub"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "azure"}, {"LOWER": "service"}, {"LOWER": "bus"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "nats"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "zeromq"}]},
            # Workflow & ETL
            {"label": "SKILL", "pattern": [{"LOWER": "airflow"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "apache"}, {"LOWER": "airflow"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "nifi"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "apache"}, {"LOWER": "nifi"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "etl"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "elt"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ssis"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "talend"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "informatica"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pentaho"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "airbyte"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "fivetran"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "stitch"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "dbt"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "dagster"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "prefect"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "luigi"}]},
            # Data Platforms
            {"label": "SKILL", "pattern": [{"LOWER": "databricks"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "delta"}, {"LOWER": "lake"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "lakehouse"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "data"}, {"LOWER": "lake"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "data"}, {"LOWER": "warehouse"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "data"}, {"LOWER": "mesh"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "data"}, {"LOWER": "pipeline"}]},
            # BI Tools
            {"label": "SKILL", "pattern": [{"LOWER": "power"}, {"LOWER": "bi"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "powerbi"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "tableau"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "looker"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "metabase"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "superset"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "apache"}, {"LOWER": "superset"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "qlik"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "qlikview"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "qliksense"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sisense"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "redash"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mode"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "domo"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "excel"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "google"}, {"LOWER": "sheets"}]},
            
            # ============================================================
            #                  MACHINE LEARNING & AI
            # ============================================================
            # Deep Learning Frameworks
            {"label": "SKILL", "pattern": [{"LOWER": "tensorflow"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pytorch"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "keras"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "jax"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mxnet"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "caffe"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "paddle"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "paddlepaddle"}]},
            # ML Libraries
            {"label": "SKILL", "pattern": [{"LOWER": "scikit-learn"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sklearn"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "xgboost"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "lightgbm"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "catboost"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "dask"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ray"}]},
            # Data Science Libraries
            {"label": "SKILL", "pattern": [{"LOWER": "pandas"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "numpy"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "scipy"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "matplotlib"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "seaborn"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "plotly"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "bokeh"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "jupyter"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "jupyter"}, {"LOWER": "notebook"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "colab"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "google"}, {"LOWER": "colab"}]},
            # NLP
            {"label": "SKILL", "pattern": [{"LOWER": "nltk"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "spacy"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "huggingface"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "hugging"}, {"LOWER": "face"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "transformers"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "bert"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gpt"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "chatgpt"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "openai"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "langchain"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "llm"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "large"}, {"LOWER": "language"}, {"LOWER": "model"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "rag"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vector"}, {"LOWER": "database"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pinecone"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "weaviate"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "milvus"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "chroma"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "faiss"}]},
            # Computer Vision
            {"label": "SKILL", "pattern": [{"LOWER": "opencv"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "yolo"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "detectron"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "detectron2"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "image"}, {"LOWER": "processing"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "computer"}, {"LOWER": "vision"}]},
            # MLOps
            {"label": "SKILL", "pattern": [{"LOWER": "mlops"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mlflow"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "kubeflow"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sagemaker"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "amazon"}, {"LOWER": "sagemaker"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vertex"}, {"LOWER": "ai"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "azure"}, {"LOWER": "ml"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "azure"}, {"LOWER": "machine"}, {"LOWER": "learning"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "weights"}, {"LOWER": "&"}, {"LOWER": "biases"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "wandb"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "neptune"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "dvc"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "bentoml"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "seldon"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "onnx"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "tensorrt"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "triton"}]},
            
            # ============================================================
            #                     CLOUD PLATFORMS
            # ============================================================
            {"label": "SKILL", "pattern": [{"LOWER": "aws"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "amazon"}, {"LOWER": "web"}, {"LOWER": "services"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "azure"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "microsoft"}, {"LOWER": "azure"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gcp"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "google"}, {"LOWER": "cloud"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "google"}, {"LOWER": "cloud"}, {"LOWER": "platform"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "alibaba"}, {"LOWER": "cloud"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "oracle"}, {"LOWER": "cloud"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ibm"}, {"LOWER": "cloud"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "digital"}, {"LOWER": "ocean"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "digitalocean"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "linode"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vultr"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "heroku"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vercel"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "netlify"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cloudflare"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "render"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "railway"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "fly.io"}]},
            # AWS Services
            {"label": "SKILL", "pattern": [{"LOWER": "ec2"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "s3"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "lambda"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "aws"}, {"LOWER": "lambda"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "rds"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ecs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "eks"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "fargate"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cloudformation"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cloudwatch"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "api"}, {"LOWER": "gateway"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cognito"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "step"}, {"LOWER": "functions"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "kinesis"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "glue"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "aws"}, {"LOWER": "glue"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "athena"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "emr"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "elasticache"}]},
            # GCP Services
            {"label": "SKILL", "pattern": [{"LOWER": "gke"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cloud"}, {"LOWER": "run"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cloud"}, {"LOWER": "functions"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "app"}, {"LOWER": "engine"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cloud"}, {"LOWER": "storage"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cloud"}, {"LOWER": "sql"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "dataflow"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "dataproc"}]},
            # Azure Services
            {"label": "SKILL", "pattern": [{"LOWER": "aks"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "azure"}, {"LOWER": "functions"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "azure"}, {"LOWER": "devops"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "azure"}, {"LOWER": "blob"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cosmos"}, {"LOWER": "db"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cosmosdb"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "azure"}, {"LOWER": "data"}, {"LOWER": "factory"}]},
            
            # ============================================================
            #                     DEVOPS & CI/CD
            # ============================================================
            # Containers & Orchestration
            {"label": "SKILL", "pattern": [{"LOWER": "docker"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "dockerfile"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "docker-compose"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "docker"}, {"LOWER": "compose"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "podman"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "kubernetes"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "k8s"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "helm"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "kustomize"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "openshift"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "rancher"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "docker"}, {"LOWER": "swarm"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mesos"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "nomad"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "istio"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "envoy"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "linkerd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "consul"}]},
            # CI/CD Tools
            {"label": "SKILL", "pattern": [{"LOWER": "jenkins"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gitlab"}, {"LOWER": "ci"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gitlab"}, {"LOWER": "ci/cd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gitlab"}, {"LOWER": "ci"}, {"TEXT": "/"}, {"LOWER": "cd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "github"}, {"LOWER": "actions"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "circleci"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "circle"}, {"LOWER": "ci"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "travis"}, {"LOWER": "ci"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "travisci"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "azure"}, {"LOWER": "pipelines"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "bamboo"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "teamcity"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "buildkite"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "drone"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "drone"}, {"LOWER": "ci"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "argocd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "argo"}, {"LOWER": "cd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "flux"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "fluxcd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "spinnaker"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "tekton"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ci/cd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ci"}, {"TEXT": "/"}, {"LOWER": "cd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cicd"}]},
            # Infrastructure as Code
            {"label": "SKILL", "pattern": [{"LOWER": "terraform"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ansible"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "puppet"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "chef"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "saltstack"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pulumi"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "crossplane"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cdk"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "aws"}, {"LOWER": "cdk"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "serverless"}, {"LOWER": "framework"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sam"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "aws"}, {"LOWER": "sam"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vagrant"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "packer"}]},
            # Monitoring & Logging
            {"label": "SKILL", "pattern": [{"LOWER": "prometheus"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "grafana"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "loki"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "datadog"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "new"}, {"LOWER": "relic"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "newrelic"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "splunk"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "elk"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "elk"}, {"LOWER": "stack"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "logstash"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "kibana"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "fluentd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "fluent"}, {"LOWER": "bit"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "jaeger"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "zipkin"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "opentelemetry"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "otel"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "apm"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "nagios"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "zabbix"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pagerduty"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "opsgenie"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sentry"}]},
            # Code Quality
            {"label": "SKILL", "pattern": [{"LOWER": "sonarqube"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sonar"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sonarlint"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "codeclimate"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "snyk"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "coverity"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "checkmarx"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "veracode"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "fortify"}]},
            
            # ============================================================
            #                 OPERATING SYSTEMS & SERVERS
            # ============================================================
            {"label": "SKILL", "pattern": [{"LOWER": "linux"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ubuntu"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "centos"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "debian"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "redhat"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "red"}, {"LOWER": "hat"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "rhel"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "fedora"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "alpine"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "arch"}, {"LOWER": "linux"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "unix"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "macos"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "windows"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "windows"}, {"LOWER": "server"}]},
            # Web Servers
            {"label": "SKILL", "pattern": [{"LOWER": "nginx"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "apache"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "apache"}, {"LOWER": "http"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "httpd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "tomcat"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "apache"}, {"LOWER": "tomcat"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "iis"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "caddy"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "traefik"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "haproxy"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gunicorn"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "uwsgi"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pm2"}]},
            
            # ============================================================
            #               VERSION CONTROL & COLLABORATION
            # ============================================================
            {"label": "SKILL", "pattern": [{"LOWER": "git"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "github"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gitlab"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "bitbucket"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "svn"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "subversion"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mercurial"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "perforce"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "azure"}, {"LOWER": "repos"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gitflow"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "trunk"}, {"LOWER": "based"}]},
            
            # ============================================================
            #                     TESTING & QA
            # ============================================================
            # Test Automation
            {"label": "SKILL", "pattern": [{"LOWER": "selenium"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cypress"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "playwright"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "puppeteer"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "webdriver"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "webdriverio"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "appium"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "espresso"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "xctest"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "detox"}]},
            # Unit Testing
            {"label": "SKILL", "pattern": [{"LOWER": "jest"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mocha"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "jasmine"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vitest"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pytest"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "unittest"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "junit"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "testng"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "nunit"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "xunit"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "rspec"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "phpunit"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gtest"}]},
            # BDD
            {"label": "SKILL", "pattern": [{"LOWER": "cucumber"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gherkin"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "behave"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "specflow"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "robot"}, {"LOWER": "framework"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "karate"}]},
            # Performance Testing
            {"label": "SKILL", "pattern": [{"LOWER": "jmeter"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gatling"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "k6"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "locust"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "artillery"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "wrk"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "loadrunner"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "blazemeter"}]},
            # API Testing
            {"label": "SKILL", "pattern": [{"LOWER": "postman"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "insomnia"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "swagger"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "openapi"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "rest"}, {"LOWER": "assured"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "newman"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "httpie"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "soapui"}]},
            # Test Concepts
            {"label": "SKILL", "pattern": [{"LOWER": "tdd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "bdd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "test"}, {"LOWER": "automation"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "manual"}, {"LOWER": "testing"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "qa"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "quality"}, {"LOWER": "assurance"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "regression"}, {"LOWER": "testing"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "integration"}, {"LOWER": "testing"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "e2e"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "end-to-end"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "smoke"}, {"LOWER": "testing"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sanity"}, {"LOWER": "testing"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "load"}, {"LOWER": "testing"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "stress"}, {"LOWER": "testing"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "performance"}, {"LOWER": "testing"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "security"}, {"LOWER": "testing"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "penetration"}, {"LOWER": "testing"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pen"}, {"LOWER": "testing"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pentest"}]},
            
            # ============================================================
            #                    API & PROTOCOLS
            # ============================================================
            {"label": "SKILL", "pattern": [{"LOWER": "rest"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "rest"}, {"LOWER": "api"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "restful"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "restful"}, {"LOWER": "api"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "graphql"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "grpc"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "soap"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "websocket"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "websockets"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "socket.io"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "http"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "https"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "http/2"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "http"}, {"TEXT": "/"}, {"TEXT": "2"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "http/3"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "http"}, {"TEXT": "/"}, {"TEXT": "3"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "tcp"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "udp"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mqtt"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "amqp"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "stomp"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "json"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "xml"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "yaml"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "protobuf"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "avro"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "thrift"}]},
            # Auth
            {"label": "SKILL", "pattern": [{"LOWER": "oauth"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "oauth2"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "oauth"}, {"TEXT": "2.0"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "jwt"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "openid"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "openid"}, {"LOWER": "connect"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "saml"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ldap"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sso"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "single"}, {"LOWER": "sign-on"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "keycloak"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "auth0"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "okta"}]},
            
            # ============================================================
            #              ARCHITECTURE & DESIGN PATTERNS
            # ============================================================
            {"label": "SKILL", "pattern": [{"LOWER": "microservices"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "microservice"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "monolithic"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "monolith"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "soa"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "service"}, {"LOWER": "oriented"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "event-driven"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "event"}, {"LOWER": "sourcing"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cqrs"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ddd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "domain"}, {"LOWER": "driven"}, {"LOWER": "design"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "hexagonal"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "clean"}, {"LOWER": "architecture"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "serverless"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "faas"}]},
            # Design Patterns
            {"label": "SKILL", "pattern": [{"LOWER": "mvc"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mvvm"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "mvp"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "oop"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "object"}, {"LOWER": "oriented"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "solid"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "dry"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "kiss"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "design"}, {"LOWER": "patterns"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "singleton"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "factory"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "observer"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "repository"}, {"LOWER": "pattern"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "functional"}, {"LOWER": "programming"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "reactive"}, {"LOWER": "programming"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "async"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "asynchronous"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "concurrency"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "multithreading"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "parallel"}, {"LOWER": "programming"}]},
            
            # ============================================================
            #           PROJECT MANAGEMENT & METHODOLOGIES
            # ============================================================
            {"label": "SKILL", "pattern": [{"LOWER": "agile"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "scrum"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "kanban"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "lean"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "waterfall"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "safe"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "devops"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "devsecops"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sre"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "site"}, {"LOWER": "reliability"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sdlc"}]},
            # PM Tools
            {"label": "SKILL", "pattern": [{"LOWER": "jira"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "confluence"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "trello"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "asana"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "notion"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "monday.com"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "clickup"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "linear"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "basecamp"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "shortcut"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "miro"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "lucidchart"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "draw.io"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "microsoft"}, {"LOWER": "project"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "slack"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "microsoft"}, {"LOWER": "teams"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "zoom"}]},
            
            # ============================================================
            #                     DESIGN TOOLS
            # ============================================================
            {"label": "SKILL", "pattern": [{"LOWER": "figma"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "adobe"}, {"LOWER": "xd"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "sketch"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "invision"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "zeplin"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "framer"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "principle"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "protopie"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "photoshop"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "adobe"}, {"LOWER": "photoshop"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "illustrator"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "adobe"}, {"LOWER": "illustrator"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "after"}, {"LOWER": "effects"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "premiere"}, {"LOWER": "pro"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "affinity"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "canva"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "blender"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "3ds"}, {"LOWER": "max"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "maya"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cinema"}, {"LOWER": "4d"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "unity"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "unreal"}, {"LOWER": "engine"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "godot"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cocos2d"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cocos"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ui/ux"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ui"}, {"TEXT": "/"}, {"LOWER": "ux"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ux/ui"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ux"}, {"TEXT": "/"}, {"LOWER": "ui"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "uml"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "bpmn"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "uml/bpmn"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "uml"}, {"TEXT": "/"}, {"LOWER": "bpmn"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ux"}, {"LOWER": "design"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ui"}, {"LOWER": "design"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "user"}, {"LOWER": "experience"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "user"}, {"LOWER": "interface"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "wireframing"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "prototyping"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "design"}, {"LOWER": "system"}]},
            
            # ============================================================
            #                       SECURITY
            # ============================================================
            {"label": "SKILL", "pattern": [{"LOWER": "owasp"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cybersecurity"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cyber"}, {"LOWER": "security"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "infosec"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "information"}, {"LOWER": "security"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "network"}, {"LOWER": "security"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "application"}, {"LOWER": "security"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cloud"}, {"LOWER": "security"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ssl"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "tls"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ssl/tls"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "ssl"}, {"TEXT": "/"}, {"LOWER": "tls"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "encryption"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "cryptography"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "firewall"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "waf"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vpn"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "iam"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "identity"}, {"LOWER": "management"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "access"}, {"LOWER": "control"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "siem"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "soc"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "vulnerability"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "threat"}, {"LOWER": "modeling"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "security"}, {"LOWER": "audit"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "gdpr"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "pci"}, {"LOWER": "dss"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "hipaa"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "iso"}, {"TEXT": "27001"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "soc2"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "soc"}, {"TEXT": "2"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "burp"}, {"LOWER": "suite"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "nmap"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "metasploit"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "kali"}, {"LOWER": "linux"}]},
            {"label": "SKILL", "pattern": [{"LOWER": "wireshark"}]},
            
            # ============================================================
            #                   BUSINESS DOMAINS
            # ============================================================
            # --- Fintech / Tài chính ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "fintech"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "financial"}, {"LOWER": "technology"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "tài"}, {"LOWER": "chính"}]},
            # --- Banking / Ngân hàng ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "banking"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "ngân"}, {"LOWER": "hàng"}]},
            # --- E-commerce / Thương mại điện tử ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "e-commerce"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "ecommerce"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "e"}, {"TEXT": "-"}, {"LOWER": "commerce"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "thương"}, {"LOWER": "mại"}, {"LOWER": "điện"}, {"LOWER": "tử"}]},
            # --- Healthcare / Y tế ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "healthcare"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "health"}, {"LOWER": "tech"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "y"}, {"LOWER": "tế"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "bệnh"}, {"LOWER": "viện"}]},
            # --- EdTech / Giáo dục ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "edtech"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "education"}, {"LOWER": "technology"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "giáo"}, {"LOWER": "dục"}]},
            # --- Logistics / Chuỗi cung ứng ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "logistics"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "supply"}, {"LOWER": "chain"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "chuỗi"}, {"LOWER": "cung"}, {"LOWER": "ứng"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "vận"}, {"LOWER": "chuyển"}]},
            # --- Real Estate / Bất động sản ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "real"}, {"LOWER": "estate"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "proptech"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "bất"}, {"LOWER": "động"}, {"LOWER": "sản"}]},
            # --- Insurance / Bảo hiểm ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "insurance"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "insurtech"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "bảo"}, {"LOWER": "hiểm"}]},
            # --- Retail / Bán lẻ ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "retail"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "bán"}, {"LOWER": "lẻ"}]},
            # --- Manufacturing / Sản xuất ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "manufacturing"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "sản"}, {"LOWER": "xuất"}]},
            # --- Telecommunications / Viễn thông ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "telecommunications"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "telecom"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "viễn"}, {"LOWER": "thông"}]},
            # --- Gaming / Game ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "gaming"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "game"}]},
            # --- Blockchain / Web3 ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "blockchain"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "cryptocurrency"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "web3"}]},
            # --- Travel / Du lịch ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "du"}, {"LOWER": "lịch"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "khách"}, {"LOWER": "sạn"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "hospitality"}]},
            # --- Entertainment ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "entertainment"}]},
            # --- HR Tech ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "hrtech"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "hr"}, {"LOWER": "tech"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "human"}, {"LOWER": "resources"}]},
            # --- AgriTech ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "agritech"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "agriculture"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "nông"}, {"LOWER": "nghiệp"}]},
            # --- Food Tech ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "foodtech"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "food"}, {"LOWER": "tech"}]},
            # --- Transportation ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "transportation"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "mobility"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "automotive"}]},
            # --- Energy ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "energy"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "cleantech"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "renewable"}, {"LOWER": "energy"}]},
            # --- Legal Tech ---
            {"label": "DOMAIN", "pattern": [{"LOWER": "legaltech"}]},
            {"label": "DOMAIN", "pattern": [{"LOWER": "legal"}, {"LOWER": "tech"}]},
        ]
        
        ruler.add_patterns(patterns)
        logger.info(f"Added {len(patterns)} entity patterns to ruler")
    
    def _add_matcher_patterns(self):
        """Add Matcher patterns for complex skill expressions"""

        # All matcher patterns removed because EntityRuler covers all required single-token skills.

        # [FIX #3] SKILL_COMBO (word/word) đã bị xóa.
        # Pattern cũ dùng IS_ALPHA/IS_ALPHA bắt MỌI cặp từ như "him/her", "full/part"...
        # EntityRuler đã có pattern cụ thể cho "ci/cd", "html/css" nên không cần matcher này.
    
    def extract(self, text: str) -> Dict[str, List[str]]:
        """
        Extract skills and domains from text using NLP
        
        :param text: Job description or requirements text
        :return: Dict with 'skills' and 'domains' lists (deduplicated)
        """
        if not text or not isinstance(text, str):
            return {'skills': [], 'domains': []}
        
        doc = self.nlp(text)
        
        skills: Set[str] = set()
        domains: Set[str] = set()
        
        # Extract from entity ruler
        for ent in doc.ents:
            if ent.label_ == "SKILL":
                normalized_skill = self._normalize_skill(ent.text)
                if normalized_skill:
                    skills.add(normalized_skill)
            elif ent.label_ == "DOMAIN":
                normalized_domain = self._normalize_domain(ent.text)
                if normalized_domain:
                    domains.add(normalized_domain)

        # Extract from matcher (removed)
        # matches = self.matcher(doc)

        # [FIX #4] PROPN heuristic đã bị xóa.
        # Heuristic cũ: nếu PROPN đứng trước "api/sdk/framework/library/database" thì add vào skills.
        # Vấn đề: bắt mọi proper noun trong văn bản dài — bao gồm tên người, tên công ty,
        # tên sản phẩm không phải skill. EntityRuler đã cover tất cả skill thực sự cần thiết.

        return {
            'skills': sorted(list(skills)),
            'domains': sorted(list(domains))
        }
    
    def _normalize_skill(self, skill_text: str) -> str:
        """Normalize skill name for consistency"""
        normalization_map = {
            # JavaScript ecosystem
            'react.js': 'React',
            'reactjs': 'React',
            'react': 'React',
            'vue.js': 'Vue',
            'vuejs': 'Vue',
            'vue': 'Vue',
            'vue2': 'Vue',
            'vue3': 'Vue',
            'angular': 'Angular',
            'angularjs': 'Angular',
            'angular.js': 'Angular',
            'angular2': 'Angular',
            'angular4': 'Angular',
            'angular8': 'Angular',
            'angular12': 'Angular',
            'angular14': 'Angular',
            'angular16': 'Angular',
            'next.js': 'Next.js',
            'nextjs': 'Next.js',
            'nuxt.js': 'Nuxt.js',
            'nuxtjs': 'Nuxt.js',
            'nuxt': 'Nuxt.js',
            'node.js': 'Node.js',
            'nodejs': 'Node.js',
            'express.js': 'Express',
            'expressjs': 'Express',
            'nest.js': 'NestJS',
            'nestjs': 'NestJS',
            # Languages
            'golang': 'Go',
            'go': 'Go',
            'python3': 'Python',
            'python2': 'Python',
            'c++': 'C++',
            'c#': 'C#',
            'c/c++': 'C/C++',
            'objective-c': 'Objective-C',
            'objectivec': 'Objective-C',
            'typescript': 'TypeScript',
            'javascript': 'JavaScript',
            # Cloud
            'aws': 'AWS',
            'gcp': 'GCP',
            'google cloud': 'GCP',
            'google cloud platform': 'GCP',
            'microsoft azure': 'Azure',
            'azure': 'Azure',
            # DevOps
            'k8s': 'Kubernetes',
            'kubernetes': 'Kubernetes',
            'docker-compose': 'Docker Compose',
            'docker compose': 'Docker Compose',
            'github actions': 'GitHub Actions',
            'gitlab ci': 'GitLab CI',
            'gitlab ci/cd': 'GitLab CI/CD',
            'circle ci': 'CircleCI',
            'circleci': 'CircleCI',
            'travis ci': 'Travis CI',
            'travisci': 'Travis CI',
            'argo cd': 'ArgoCD',
            'argocd': 'ArgoCD',
            'ci/cd': 'CI/CD',
            'cicd': 'CI/CD',
            # Databases
            'postgresql': 'PostgreSQL',
            'postgres': 'PostgreSQL',
            'mongodb': 'MongoDB',
            'mysql': 'MySQL',
            'mariadb': 'MariaDB',
            'ms sql': 'MS SQL Server',
            'mssql': 'MS SQL Server',
            'sql server': 'MS SQL Server',
            't-sql': 'T-SQL',
            'pl/sql': 'PL/SQL',
            'plsql': 'PL/SQL',
            'dynamodb': 'DynamoDB',
            'elasticsearch': 'Elasticsearch',
            'elastic search': 'Elasticsearch',
            'redis': 'Redis',
            'big query': 'BigQuery',
            'bigquery': 'BigQuery',
            'power bi': 'Power BI',
            'powerbi': 'Power BI',
            # ML/AI
            'scikit-learn': 'Scikit-learn',
            'sklearn': 'Scikit-learn',
            'tensorflow': 'TensorFlow',
            'pytorch': 'PyTorch',
            'huggingface': 'Hugging Face',
            'hugging face': 'Hugging Face',
            'openai': 'OpenAI',
            'chatgpt': 'ChatGPT',
            'llm': 'LLM',
            'large language model': 'LLM',
            # Mobile
            'react native': 'React Native',
            'flutter': 'Flutter',
            'swiftui': 'SwiftUI',
            'swift ui': 'SwiftUI',
            'kotlin multiplatform': 'Kotlin Multiplatform',
            'android studio': 'Android Studio',
            'ios sdk': 'iOS SDK',
            'android sdk': 'Android SDK',
            'jetpack compose': 'Jetpack Compose',
            # Frontend
            'html5': 'HTML5',
            'html 5': 'HTML5',
            'css3': 'CSS3',
            'css 3': 'CSS3',
            'tailwind css': 'Tailwind CSS',
            'tailwindcss': 'Tailwind CSS',
            'material ui': 'Material UI',
            'material-ui': 'Material UI',
            'ant design': 'Ant Design',
            'styled-components': 'Styled Components',
            'chakra ui': 'Chakra UI',
            # Backend
            'spring boot': 'Spring Boot',
            'springboot': 'Spring Boot',
            'spring framework': 'Spring',
            'spring mvc': 'Spring MVC',
            'spring cloud': 'Spring Cloud',
            'spring security': 'Spring Security',
            'spring data': 'Spring Data',
            '.net core': '.NET Core',
            'dotnet core': '.NET Core',
            'asp.net core': 'ASP.NET Core',
            'entity framework': 'Entity Framework',
            'ef core': 'EF Core',
            'ruby on rails': 'Ruby on Rails',
            # Message Queues
            'apache kafka': 'Kafka',
            'kafka': 'Kafka',
            'rabbitmq': 'RabbitMQ',
            'rabbit mq': 'RabbitMQ',
            'activemq': 'ActiveMQ',
            'active mq': 'ActiveMQ',
            'amazon sqs': 'SQS',
            'azure service bus': 'Azure Service Bus',
            # Data
            'apache spark': 'Spark',
            'pyspark': 'PySpark',
            'apache airflow': 'Airflow',
            'apache flink': 'Flink',
            'apache beam': 'Apache Beam',
            'apache nifi': 'NiFi',
            'apache superset': 'Superset',
            'delta lake': 'Delta Lake',
            'data lake': 'Data Lake',
            'data warehouse': 'Data Warehouse',
            'data pipeline': 'Data Pipeline',
            'data mesh': 'Data Mesh',
            # Testing
            'test automation': 'Test Automation',
            'manual testing': 'Manual Testing',
            'quality assurance': 'QA',
            'robot framework': 'Robot Framework',
            'rest assured': 'REST Assured',
            'load testing': 'Load Testing',
            'stress testing': 'Stress Testing',
            'performance testing': 'Performance Testing',
            'penetration testing': 'Penetration Testing',
            'pen testing': 'Penetration Testing',
            # Monitoring
            'new relic': 'New Relic',
            'newrelic': 'New Relic',
            'elk stack': 'ELK Stack',
            'fluent bit': 'Fluent Bit',
            # Architecture
            'microservice': 'Microservices',
            'microservices': 'Microservices',
            'service oriented': 'SOA',
            'event-driven': 'Event-Driven',
            'event sourcing': 'Event Sourcing',
            'domain driven design': 'DDD',
            'clean architecture': 'Clean Architecture',
            'object oriented': 'OOP',
            'design patterns': 'Design Patterns',
            'functional programming': 'Functional Programming',
            'reactive programming': 'Reactive Programming',
            'parallel programming': 'Parallel Programming',
            # Protocols
            'rest api': 'REST API',
            'restful api': 'RESTful API',
            'graphql': 'GraphQL',
            'websocket': 'WebSocket',
            'websockets': 'WebSocket',
            'socket.io': 'Socket.IO',
            'openid connect': 'OpenID Connect',
            'single sign-on': 'SSO',
            # Security
            'ssl/tls': 'SSL/TLS',
            'cyber security': 'Cybersecurity',
            'information security': 'Information Security',
            'network security': 'Network Security',
            'application security': 'Application Security',
            'cloud security': 'Cloud Security',
            'identity management': 'IAM',
            'access control': 'Access Control',
            'threat modeling': 'Threat Modeling',
            'security audit': 'Security Audit',
            'kali linux': 'Kali Linux',
            'burp suite': 'Burp Suite',
            # OS
            'red hat': 'Red Hat',
            'windows server': 'Windows Server',
            'arch linux': 'Arch Linux',
            # Servers
            'apache http': 'Apache',
            'apache tomcat': 'Tomcat',
            # PM/Methodology
            'site reliability': 'SRE',
            'microsoft project': 'MS Project',
            'microsoft teams': 'Microsoft Teams',
            # Design
            'adobe xd': 'Adobe XD',
            'adobe photoshop': 'Photoshop',
            'adobe illustrator': 'Illustrator',
            'after effects': 'After Effects',
            'premiere pro': 'Premiere Pro',
            '3ds max': '3ds Max',
            'cinema 4d': 'Cinema 4D',
            'unreal engine': 'Unreal Engine',
            'ui/ux': 'UI/UX',
            'ux design': 'UX Design',
            'ui design': 'UI Design',
            'user experience': 'UX',
            'user interface': 'UI',
            'design system': 'Design System',
        }
        
        skill_lower = skill_text.lower().strip()
        
        if skill_lower in normalization_map:
            return normalization_map[skill_lower]
        
        # Fallback: try without spaces to handle Spacy multi-token patterns
        # e.g. ent.text="Java 8" → key="java8", ent.text="Angular 12" → key="angular12"
        compact_key = skill_lower.replace(" ", "")
        if compact_key != skill_lower and compact_key in normalization_map:
            return normalization_map[compact_key]
        
        # Default: return as-is but handle some capitalization
        if skill_text == "Go":
            return "Go"
        
        return skill_text.strip()
    
    def _normalize_domain(self, domain_text: str) -> str:
        """Normalize domain name for consistency"""
        normalization_map = {
            'fintech': 'Fintech',
            'financial technology': 'Fintech',
            'tài chính': 'Fintech',
            'banking': 'Banking',
            'ngân hàng': 'Banking',
            'e-commerce': 'E-commerce',
            'ecommerce': 'E-commerce',
            'thương mại điện tử': 'E-commerce',
            'healthcare': 'Healthcare',
            'health tech': 'Healthcare',
            'y tế': 'Healthcare',
            'bệnh viện': 'Healthcare',
            'edtech': 'EdTech',
            'education technology': 'EdTech',
            'giáo dục': 'EdTech',
            'logistics': 'Logistics',
            'supply chain': 'Logistics',
            'chuỗi cung ứng': 'Logistics',
            'vận chuyển': 'Logistics',
            'real estate': 'Real Estate',
            'proptech': 'Real Estate',
            'bất động sản': 'Real Estate',
            'insurance': 'Insurance',
            'insurtech': 'Insurance',
            'bảo hiểm': 'Insurance',
            'retail': 'Retail',
            'bán lẻ': 'Retail',
            'manufacturing': 'Manufacturing',
            'sản xuất': 'Manufacturing',
            'telecommunications': 'Telecommunications',
            'telecom': 'Telecommunications',
            'viễn thông': 'Telecommunications',
            'gaming': 'Gaming',
            'game': 'Gaming',
            'blockchain': 'Blockchain',
            'web3': 'Blockchain',
            'cryptocurrency': 'Blockchain',
            'du lịch': 'Travel',
            'khách sạn': 'Hospitality',
            'hospitality': 'Hospitality',
            'entertainment': 'Entertainment',
            'hrtech': 'HR Tech',
            'hr tech': 'HR Tech',
            'human resources': 'HR Tech',
            'agritech': 'AgriTech',
            'agriculture': 'AgriTech',
            'nông nghiệp': 'AgriTech',
            'foodtech': 'FoodTech',
            'food tech': 'FoodTech',
            'transportation': 'Transportation',
            'mobility': 'Transportation',
            'automotive': 'Automotive',
            'energy': 'Energy',
            'cleantech': 'CleanTech',
            'renewable energy': 'CleanTech',
            'legaltech': 'LegalTech',
            'legal tech': 'LegalTech',
        }
        
        domain_lower = domain_text.lower().strip()
        
        if domain_lower in normalization_map:
            return normalization_map[domain_lower]
        
        return domain_text.strip()
    
    def extract_skills_only(self, text: str) -> List[str]:
        """Convenience method to extract only skills"""
        return self.extract(text)['skills']
    
    def extract_domains_only(self, text: str) -> List[str]:
        """Convenience method to extract only domains"""
        return self.extract(text)['domains']

    def get_skill_whitelist(self) -> set[str]:
        """
        Trả về tập hợp tất cả skill name đã được định nghĩa trong patterns.
        Dùng để filter skills_tags trước khi insert DB.
        """
        whitelist = set()
        for pattern in self.nlp.get_pipe("entity_ruler").patterns:
            if pattern.get("label") == "SKILL":
                p = pattern["pattern"]
                if isinstance(p, str):
                    whitelist.add(p.lower())
                elif isinstance(p, list):
                    tokens = []
                    for t in p:
                        val = t.get("LOWER", t.get("TEXT", ""))
                        if isinstance(val, str):
                            tokens.append(val)
                        # skip dict values like {"REGEX": "..."} — not a concrete skill name
                    if tokens:
                        whitelist.add(" ".join(tokens).lower())
        return whitelist


# Singleton instance
_extractor_instance = None

def get_skill_extractor() -> SkillExtractor:
    """Get or create singleton SkillExtractor instance"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = SkillExtractor()
    return _extractor_instance
