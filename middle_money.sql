/*
Navicat MySQL Data Transfer

Source Server         : 127.0.0.1
Source Server Version : 50643
Source Host           : localhost:3306
Source Database       : svb

Target Server Type    : MYSQL
Target Server Version : 50643
File Encoding         : 65001ls


Date: 2020-03-12 16:33:29
*/

SET FOREIGN_KEY_CHECKS=0;

-- ----------------------------
-- Table structure for middle_money
-- ----------------------------
DROP TABLE IF EXISTS `middle_money`;
CREATE TABLE `middle_money` (
  `id` mediumint(11) NOT NULL AUTO_INCREMENT,
  `middle_id` int(11) DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `card_num` int(11) DEFAULT NULL,
  `create_price` float(11,2) DEFAULT NULL,
  `sum_money` float(11,2) DEFAULT NULL,
  `create_time` datetime DEFAULT NULL,
  `pay_status` varchar(255) DEFAULT NULL,
  `pay_time` datetime DEFAULT NULL,
  `detail` text,
  `note` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `middle_id` (`middle_id`) USING BTREE,
  CONSTRAINT `middle_money_ibfk_1` FOREIGN KEY (`middle_id`) REFERENCES `middle` (`id`) ON DELETE CASCADE ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
