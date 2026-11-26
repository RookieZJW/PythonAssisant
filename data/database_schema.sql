
-- ============================================
-- Python 智能助手 - 数据库结构
-- 数据库名: smart_assistant
-- 字符集: utf8mb4
-- ============================================

CREATE DATABASE IF NOT EXISTS smart_assistant
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE smart_assistant;

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
DROP TABLE IF EXISTS `kb_chunks`;
CREATE TABLE `kb_chunks` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `kb_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `doc_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `doc_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `position` int DEFAULT 0,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_kb_chunks_kb` (`kb_id`),
  KEY `ix_kb_chunks_doc` (`doc_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
DROP TABLE IF EXISTS `kb_documents`;
CREATE TABLE `kb_documents` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `kb_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `filename` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` mediumtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `size` int DEFAULT 0,
  `chunk_count` int DEFAULT 0,
  `original_path` varchar(512) DEFAULT NULL,
  `table_count` int DEFAULT 0,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_kb_documents_kb` (`kb_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
DROP TABLE IF EXISTS `kb_tables`;
CREATE TABLE `kb_tables` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `kb_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `doc_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `doc_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `table_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `source` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `rows_json` mediumtext COLLATE utf8mb4_unicode_ci DEFAULT '[]',
  `merges_json` mediumtext COLLATE utf8mb4_unicode_ci DEFAULT '[]',
  `row_count` int DEFAULT 0,
  `col_count` int DEFAULT 0,
  `fill_rate` float DEFAULT 0,
  `original_path` varchar(512) DEFAULT NULL,
  `original_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_kb_tables_kb` (`kb_id`),
  KEY `ix_kb_tables_doc` (`doc_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
DROP TABLE IF EXISTS `kb_shares`;
CREATE TABLE `kb_shares` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `kb_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `owner_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `shared_with` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_kb_share` (`kb_id`,`shared_with`),
  KEY `ix_kb_shares_user` (`shared_with`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
DROP TABLE IF EXISTS `knowledge_bases`;
CREATE TABLE `knowledge_bases` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `user_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_kb_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
DROP TABLE IF EXISTS `conversations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `conversations` (
  `id` varchar(36) NOT NULL,
  `title` varchar(200) NOT NULL,
  `user_id` varchar(64) DEFAULT NULL,
  `model` varchar(32) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `role_id` varchar(36) DEFAULT NULL,
  `mode` varchar(16) NOT NULL DEFAULT 'normal',
  `kb_id` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_conversations_user_id` (`user_id`),
  KEY `ix_conversations_mode` (`mode`),
  KEY `ix_conversations_kb_id` (`kb_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `messages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `conversation_id` varchar(36) CHARACTER SET utf8mb3 NOT NULL,
  `role` varchar(16) CHARACTER SET utf8mb3 NOT NULL,
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `tokens` int DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_messages_conversation_id` (`conversation_id`),
  CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=263 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `roles` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `prompt` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `icon` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_builtin` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` varchar(64) NOT NULL,
  `username` varchar(50) DEFAULT NULL,
  `password_hash` varchar(200) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `wechat_openid` varchar(100) DEFAULT NULL,
  `qq_openid` varchar(100) DEFAULT NULL,
  `nickname` varchar(50) DEFAULT '用户',
  `avatar` varchar(200) DEFAULT '',
  `api_key` varchar(64) DEFAULT NULL,
  `quota` int DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `api_key` (`api_key`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `phone` (`phone`),
  UNIQUE KEY `wechat_openid` (`wechat_openid`),
  UNIQUE KEY `qq_openid` (`qq_openid`),
  UNIQUE KEY `api_key_2` (`api_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

