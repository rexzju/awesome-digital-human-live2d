# Awesome-Digital-Human 本地调试指南

## 一、使用Docker Compose启动完整服务

### 1. 构建Docker镜像
```bash
docker build -f docker/adhWeb.Dockerfile -t adh-web:0.1 .
docker build -f docker/adhServer.Dockerfile -t adh-server:0.1 .
```

### 2. 启动所有服务
```bash
docker-compose up -d
```

### 3. 访问服务
- Web界面: http://localhost:8080
- API服务: http://localhost:8880

### 4. 局域网访问设置
使用Docker Compose启动时，服务默认已经配置为允许局域网访问，其他设备可以通过以下方式访问：
- Web界面: http://[你的电脑IP]:8080
- API服务: http://[你的电脑IP]:8880

> 注意：确保你的防火墙允许这些端口的访问

## 二、本地开发环境调试（无需Docker）

### 后端服务启动

#### 1. 安装依赖
```bash
cd /Users/rexyu/Desktop/dev/github/awesome-digital-human-live2d
pip install -r requirements.txt
```

#### 2. 配置文件设置
复制配置模板并根据需要修改：
```bash
cp configs/config_template.yaml configs/config.yaml
# 根据需要编辑config.yaml文件
```

#### 3. 启动后端服务
```bash
python3 main.py
```

后端服务默认已配置为允许局域网访问（通过config_template.yaml中的`SERVER.IP: "0.0.0.0"`设置）。
- 本地访问: http://localhost:3000
- 局域网访问: http://[你的电脑IP]:3000

### 前端服务启动

#### 1. 安装依赖
```bash
cd /Users/rexyu/Desktop/dev/github/awesome-digital-human-live2d/web
# 安装pnpm（如果尚未安装）
npm install -g pnpm
# 安装项目依赖
pnpm install
```

#### 2. 配置环境变量
编辑.env文件，设置正确的后端服务地址：
```bash
# 取消注释并设置为你的电脑IP地址
NEXT_PUBLIC_SERVER_IP="你的电脑IP地址"
NEXT_PUBLIC_SERVER_PROTOCOL="http"
NEXT_PUBLIC_SERVER_PORT="8880"
NEXT_PUBLIC_SERVER_VERSION="v0"
NEXT_PUBLIC_SERVER_MODE="dev"
```

#### 3. 启动前端开发服务器（允许局域网访问）
```bash
# 使用--host参数允许局域网访问
pnpm run dev -- --host
```

- 本地访问: http://localhost:3000
- 局域网访问: http://[你的电脑IP]:3000

> 注意：确保你的防火墙允许3000和8880端口的访问

## 三、如何查找电脑的IP地址

### 在Mac系统中
```bash
ifconfig
```
在输出中查找`inet`地址，通常以`192.168.x.x`或`10.x.x.x`开头的地址就是你的局域网IP地址。

### 在Windows系统中
```cmd
ipconfig
```
查找`IPv4 地址`，通常以`192.168.x.x`或`10.x.x.x`开头的地址就是你的局域网IP地址。

### 在Linux系统中
```bash
ip addr show
```
查找`inet`地址，通常以`192.168.x.x`或`10.x.x.x`开头的地址就是你的局域网IP地址。

## 四、关于Nginx的使用说明

### 生产环境
在生产环境或完整Docker部署中，**需要Nginx**，它的主要作用是：
1. 作为反向代理，将请求路由到不同的服务
2. 提供HTTPS支持
3. 处理静态资源

### 本地开发环境
在**本地开发调试**时，**不需要Nginx**，原因如下：
1. 前端开发服务器（pnpm run dev）可以直接访问后端API
2. 可以通过配置CORS解决跨域问题
3. 开发环境通常不需要HTTPS

### 本地开发时的API访问方式
在本地开发环境中，前端可以直接访问：
- 后端API: http://localhost:8880

## 五、调试技巧

### 1. 查看日志
Docker环境下查看日志：
```bash
docker-compose logs -f
```

### 2. 单独重启某个服务
```bash
docker-compose restart adh-api
```

### 3. 热重载
- 前端开发服务器支持热重载，修改代码后会自动刷新
- 后端服务需要手动重启以应用更改

## 六、配置说明

### 环境变量
前端需要配置的主要环境变量：
- API_BASE_URL: 后端API地址

### 代理配置
如果需要模拟生产环境的代理配置，可以在前端项目的next.config.js中配置代理：
```javascript
module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8880/:path*',
      },
    ]
  },
}
```