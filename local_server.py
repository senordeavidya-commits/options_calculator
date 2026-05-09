from http.server import HTTPServer, CGIHTTPRequestHandler
import os

# 这是一个极其简易的本地服务器，可以同时托管 HTML 和执行 api 文件夹里的 Python
class Handler(CGIHTTPRequestHandler):
    cgi_directories = ["/api"]

port = 8000
print(f"🚀 定价器本地测试服务器已启动: http://localhost:{port}/projects/option-pricing.html")
httpd = HTTPServer(('', port), Handler)
httpd.serve_forever()