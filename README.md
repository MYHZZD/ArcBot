# ArcBot
A nice bot
## reply插件指令说明
### 指令
**/学习 A B**  
检测到A发送B，A为完整的消息内容  
**/关键词 C D**  
检测到C发送D，C可为消息内关键词  
**/删除 A**  
删除由A启动的对话（不是关键词）  
**/关键词删除 C**  
删除关键词C  
**/学习列表**  
列出所有A（不是关键词）  
**/关键词列表**  
列出所有C（关键词）  
**/启用回复功能**  
插件总开关  
**/禁用回复功能**  
禁用除代码内部定义回复外所有回复  
**/添加管理员**  
增加插件管理员（各群不互通）  
**/封禁**  
取消用户使用/学习 /删除等功能的权限，被封禁用户设置的关键词不会触发对话  
### 回复逻辑
/学习 的参数A为全句，/关键词 功能的参数C为句中关键词  
当有相同的A与C存在，且由全句A触发回复，会回复/学习功能的参数B，即覆盖关键词功能  
例:  
指令1 /学习 早 早安  
指令2 /关键词 早 早呀~  
用户输入:早  
回复:早安  
用户输入:早上好  
回复:早呀~  
  
管理员可以禁用回复功能、添加管理员、封禁  
## Morning插件指令说明
### 指令
**/Morning**  
开启自动回复  
**/disMorning**  
关闭自动回复  