CREATE TABLE `account`  (
  `accountId` char(30) NOT NULL,
  `email` varchar(255) NOT NULL,
  `pw` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `atCreated` datetime NOT NULL,
  `admin` tinyint ZEROFILL NOT NULL COMMENT '0表示否，其它表示是',
  `beInGroupId` char(30) NULL,
  `applicationGroupId` char(30) NULL,
  PRIMARY KEY (`accountId`),
  UNIQUE INDEX `sy2`(`email`) USING BTREE
);

CREATE TABLE `files`  (
  `fileId` char(30) NOT NULL,
  `name` varchar(255) NOT NULL,
  `label` varchar(255) NOT NULL,
  `atDeleted` datetime NULL,
  `groupId` char(30) NULL,
  `atCreated` datetime NOT NULL,
  `size` bigint NOT NULL,
  `uploader` char(30) NULL,
  PRIMARY KEY (`fileId`)
);

CREATE TABLE `groupAndSpecific`  (
  `specificPageId` char(30) NOT NULL,
  `provideToGroupId` char(30) NOT NULL,
  PRIMARY KEY (`specificPageId`, `provideToGroupId`)
);

CREATE TABLE `groups`  (
  `groupId` char(30) NOT NULL,
  `name` varchar(255) NOT NULL,
  `storageFieldKey` char(30) NOT NULL,
  `publicPageId` char(30) NOT NULL,
  `publicPageAnnouncement` varchar(255) NOT NULL,
  PRIMARY KEY (`groupId`),
  UNIQUE INDEX `sy1`(`publicPageId`) USING BTREE
);

CREATE TABLE `publicPageAndFile`  (
  `publicPageId` char(30) NOT NULL,
  `fileId` char(30) NOT NULL,
  PRIMARY KEY (`publicPageId`, `fileId`)
);

CREATE TABLE `specificPage`  (
  `specificPageId` char(30) NOT NULL,
  `ownerGroupId` char(30) NOT NULL,
  `announcement` varchar(255) NOT NULL,
  PRIMARY KEY (`specificPageId`)
);

CREATE TABLE `specificPageAndFile`  (
  `specificPageId` char(30) NOT NULL,
  `fileId` char(30) NOT NULL,
  PRIMARY KEY (`specificPageId`, `fileId`)
);

CREATE TABLE `sysAccount`  (
  `id` char(30) NOT NULL,
  `pw` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
);

ALTER TABLE `account` ADD CONSTRAINT `fk_account_group_1` FOREIGN KEY (`beInGroupId`) REFERENCES `groups` (`groupId`) ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE `account` ADD CONSTRAINT `fk_account_group_2` FOREIGN KEY (`applicationGroupId`) REFERENCES `groups` (`groupId`) ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE `files` ADD CONSTRAINT `fk_file_group_1` FOREIGN KEY (`groupId`) REFERENCES `groups` (`groupId`) ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE `files` ADD CONSTRAINT `fk_file_account_2` FOREIGN KEY (`uploader`) REFERENCES `account` (`accountId`) ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE `groupAndSpecific` ADD CONSTRAINT `fk_groupAndSpecific_specificPage_1` FOREIGN KEY (`specificPageId`) REFERENCES `specificPage` (`specificPageId`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `groupAndSpecific` ADD CONSTRAINT `fk_groupAndSpecific_group_2` FOREIGN KEY (`provideToGroupId`) REFERENCES `groups` (`groupId`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `publicPageAndFile` ADD CONSTRAINT `fk_publicPageAndFile_group_1` FOREIGN KEY (`publicPageId`) REFERENCES `groups` (`publicPageId`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `publicPageAndFile` ADD CONSTRAINT `fk_publicPageAndFile_file_2` FOREIGN KEY (`fileId`) REFERENCES `files` (`fileId`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `specificPage` ADD CONSTRAINT `fk_specificPage_group_1` FOREIGN KEY (`ownerGroupId`) REFERENCES `groups` (`groupId`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `specificPageAndFile` ADD CONSTRAINT `fk_specificPageAndFile_file_1` FOREIGN KEY (`fileId`) REFERENCES `files` (`fileId`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `specificPageAndFile` ADD CONSTRAINT `fk_specificPageAndFile_specificPage_2` FOREIGN KEY (`specificPageId`) REFERENCES `specificPage` (`specificPageId`) ON DELETE CASCADE ON UPDATE CASCADE;

