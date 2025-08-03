-- MySQL dump 10.13  Distrib 8.0.41, for Win64 (x86_64)
--
-- Host: localhost    Database: user_system
-- ------------------------------------------------------
-- Server version	8.0.41

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

--
-- Current Database: `user_system`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `WTB_SQL` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `WTB_SQL`;

--
-- Table structure for table `chapters`
--

DROP TABLE IF EXISTS `chapters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chapters` (
  `id` int NOT NULL AUTO_INCREMENT,
  `wtb_id` int NOT NULL,
  `name` varchar(255) NOT NULL,
  `topic_count` int DEFAULT '0',
  `correct_rate` float DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `wtb_id` (`wtb_id`),
  CONSTRAINT `chapters_ibfk_1` FOREIGN KEY (`wtb_id`) REFERENCES `wtbs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `daily_review_stats`
--

DROP TABLE IF EXISTS `daily_review_stats`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `daily_review_stats` (
  `id` int NOT NULL AUTO_INCREMENT,
  `wtb_id` int NOT NULL,
  `user_id` int NOT NULL,
  `date` date NOT NULL,
  `review_count` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_idx` (`wtb_id`,`user_id`,`date`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `review_logs`
--

DROP TABLE IF EXISTS `review_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `review_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL COMMENT '用户ID',
  `wtb_id` int NOT NULL DEFAULT '0',
  `wtp_id` int DEFAULT NULL,
  `wrong_topic_id` int NOT NULL COMMENT '错题ID',
  `review_time` datetime NOT NULL COMMENT '复习时间',
  `accuracy` float DEFAULT '0' COMMENT '复习准确率，0~1之间，默认0',
  `source` enum('daily_set','manual','edit') DEFAULT 'daily_set' COMMENT '数据来源',
  `remark` text COMMENT '备注信息',
  PRIMARY KEY (`id`),
  KEY `idx_user_wtb_topic` (`user_id`,`wtp_id`,`wrong_topic_id`),
  KEY `fk_review_logs_wrong_topic` (`wrong_topic_id`),
  CONSTRAINT `fk_review_logs_wrong_topic` FOREIGN KEY (`wrong_topic_id`) REFERENCES `wrong_topic` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户后续重做错题的记录';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(255) NOT NULL,
  `password_hash` varchar(64) NOT NULL,
  `nickname` varchar(64) DEFAULT NULL,
  `avatar_url` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wrong_topic`
--

DROP TABLE IF EXISTS `wrong_topic`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `wrong_topic` (
  `id` int NOT NULL AUTO_INCREMENT,
  `wtb_id` int NOT NULL,
  `unit_id` int DEFAULT NULL,
  `title` varchar(255) NOT NULL,
  `file_path` varchar(500) DEFAULT NULL,
  `init_score` float NOT NULL DEFAULT '0',
  `quality_weight` float NOT NULL DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `is_reviewed` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否至少复习过，0否1是',
  `answer_file_path` varchar(500) DEFAULT NULL,
  `is_flippable` tinyint(1) DEFAULT '0',
  `explanation_url` varchar(500) DEFAULT NULL COMMENT '讲解链接',
  `last_review_date` datetime DEFAULT NULL,
  `current_correct_rate` float DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `wtb_id` (`wtb_id`),
  KEY `unit_id` (`unit_id`),
  CONSTRAINT `wrong_topic_ibfk_1` FOREIGN KEY (`wtb_id`) REFERENCES `wtbs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=645 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wrong_topic_paper`
--

DROP TABLE IF EXISTS `wrong_topic_paper`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `wrong_topic_paper` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `wtb_id` int NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `question_count` int NOT NULL,
  `title` varchar(100) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `wtb_id` (`wtb_id`),
  CONSTRAINT `wrong_topic_paper_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `wrong_topic_paper_ibfk_2` FOREIGN KEY (`wtb_id`) REFERENCES `wtbs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wrong_topic_paper_rel`
--

DROP TABLE IF EXISTS `wrong_topic_paper_rel`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `wrong_topic_paper_rel` (
  `id` int NOT NULL AUTO_INCREMENT,
  `wrong_topic_paper_id` int NOT NULL,
  `wrong_topic_id` int NOT NULL,
  `score_ratio` float DEFAULT NULL,
  `is_flippable` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `wrong_topic_paper_id` (`wrong_topic_paper_id`),
  KEY `wrong_topic_id` (`wrong_topic_id`),
  CONSTRAINT `wrong_topic_paper_rel_ibfk_1` FOREIGN KEY (`wrong_topic_paper_id`) REFERENCES `wrong_topic_paper` (`id`) ON DELETE CASCADE,
  CONSTRAINT `wrong_topic_paper_rel_ibfk_2` FOREIGN KEY (`wrong_topic_id`) REFERENCES `wrong_topic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `wrong_topic_paper_rel_chk_1` CHECK (((`score_ratio` >= 0) and (`score_ratio` <= 1)))
) ENGINE=InnoDB AUTO_INCREMENT=71 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wrong_topic_tag_rel`
--

DROP TABLE IF EXISTS `wrong_topic_tag_rel`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `wrong_topic_tag_rel` (
  `id` int NOT NULL AUTO_INCREMENT,
  `wrong_topic_id` int NOT NULL,
  `tag_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `wrong_topic_id` (`wrong_topic_id`,`tag_id`),
  KEY `tag_id` (`tag_id`),
  CONSTRAINT `wrong_topic_tag_rel_ibfk_1` FOREIGN KEY (`wrong_topic_id`) REFERENCES `wrong_topic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `wrong_topic_tag_rel_ibfk_2` FOREIGN KEY (`tag_id`) REFERENCES `wrong_topic_tags` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=85 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wrong_topic_tags`
--

DROP TABLE IF EXISTS `wrong_topic_tags`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `wrong_topic_tags` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `tag_name` varchar(50) NOT NULL,
  `weight` float NOT NULL DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `color` varchar(7) DEFAULT '#000000',
  `wtb_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_tag_unique` (`user_id`,`wtb_id`,`tag_name`),
  KEY `fk_tag_wtb` (`wtb_id`),
  CONSTRAINT `fk_tag_wtb` FOREIGN KEY (`wtb_id`) REFERENCES `wtbs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wtb_notes`
--

DROP TABLE IF EXISTS `wtb_notes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `wtb_notes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `wtb_id` int NOT NULL,
  `note_text` text NOT NULL,
  `user` varchar(100) NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `wrong_topic_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `wtb_id` (`wtb_id`),
  KEY `fk_wrong_topic_id` (`wrong_topic_id`),
  CONSTRAINT `fk_wrong_topic_id` FOREIGN KEY (`wrong_topic_id`) REFERENCES `wrong_topic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `wtb_notes_ibfk_1` FOREIGN KEY (`wtb_id`) REFERENCES `wtbs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wtbs`
--

DROP TABLE IF EXISTS `wtbs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `wtbs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `title` varchar(255) NOT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `wrong_count` int DEFAULT '0',
  `label_color` varchar(10) DEFAULT '#FFFFFF',
  `daily_topic_num` int NOT NULL DEFAULT '5' COMMENT '每日自动生成题目数量',
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `wtbs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-07-31 14:25:31
