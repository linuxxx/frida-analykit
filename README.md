# Frida-Analykit

[![GitHub Stars](https://img.shields.io/github/stars/zsa233/frida-analykit)](https://github.com/zsa233/frida-analykit/stargazers)
[![License](https://img.shields.io/github/license/zsa233/frida-analykit)](LICENSE)


🌍 语言: 中文 | [English](README_EN.md)


## 简介

**⚠目前仅支持arm64**

> frida分析工具，用于在注入调试过程快速构建基础工具方法，以便专注于实际问题的解决。

1. 使用`python`来rpc代理`js`层的所有输入和输出
    - 使用`JsHandle`来代理`js`的变量，实现间接的`python-REPL`来近似`js-REPL`进行调试。
    - 解决原生的js日志输出和`js-REPL`抢夺控制台输入的重叠输出问题。
    - 解决当日志/数据输出时归档和分析时繁琐的手动文件拉取操作。

2. 使用`frida-compile`来支持模块化开发

3. 针对通用而非特殊场景设计和实现的工具方法


## 工具套件

| 名称 | 可用性 | 备注 |
|:---------|:-----:|:-----|
| nettools | √     | 抓包辅助 |
| elftools | √     | .so解析辅助; symbol-attach(TODO) |
| jnitools | TODO  | jni辅助; jni_java(TODO) |
| dextools | TODO  | dex辅助 |


## 用法

**该工具建议`fork`自己的项目用于自定义修改或`git clone`的方式来使用**

以下步骤将构建如下层级目录结构
```md
myproj
├── frida-analykit/
│   ├── agent/
│   ├── script/
│   ├── templates/
│   ├── gen.py
│   ├── main.py
│   └── ...
│
├── config.yml
├── index.ts
├── ptpython_spawn.sh
├── package.json
└── ...

```


1. 拉取脚本
```sh
# (单项目建议) 在工作目录下直接git clone：
# (多项目建议) 使用软连接的方式连接到当前工作目录
# 工作路径：myproj
git clone https://github.com/ZSA233/frida-analykit.git

```

2. 生成工作环境

```sh
# 在这之前选定自己想要指定的全局或者pyenv环境来安装依赖.
# pip install -r requirements.txt

# 生成环境文件（在当前目录生成index.ts, config.yml, ptpython_spaw.sh等帮助脚本和配置）
python frida-analykit/gen.py dev

```

3. 配置config.yml
> 配置文件: `config.yml`

```yml

# 目标包名（必填
app: 
# frida-compile 自动生成的 代理脚本
jsfile: _agent.js


server:
  # frida-server在目标调试设备上面的bin路径
  servername: /data/local/tmp/frida-server
  # adb forward 映射到本机的流量地址端口
  host: 127.0.0.1:6666
  # 多设备时候需要指定的device_id（使用adb devices确定）
  device: aaaaaaaa

agent:
  # 任何从js脚本中使用send来传输data，未注册处理器的类型都会默认保存在这个目录下
  datadir: ./data/
  stdout: ./logs/outerr.log
  stderr: ./logs/outerr.log


script:
  nettools:
    ssl_log_secret: ./data/nettools/sslkey/

```


4. 启动frida-compile文件监听编译
```sh
# 执行下面命令行来监听index.ts脚本的修改变动以实时编译生成_agent.js
npm run watch
```

5. 启动frida-server服务
```sh
python frida-analykit/main.py bootup-server
```

6. 运行脚本

```sh
# 按照
# 1. 使用repl来启动spawn/attach注入
./ptpython_spawn.sh
./ptpython_attach.sh

# 2. 脚本直接运行
python frida-analykit/main.py spawn

```


## 平台

| 平台 | 是否兼容 |
|:---:|:----:|
| win | 支持wsl |
| linux | √ |
| macos | √ |


## 例子

[android-reverse-examples](https://github.com/ZSA233/android-reverse-examples)

