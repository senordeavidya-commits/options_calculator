import http.server
import socketserver
import json

PORT = 8000

class LocalDevHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        # 拦截前端发往 /api/pricing 的请求
        if self.path == '/api/pricing':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data)
            
            print(f"\n📥 收到前端请求参数:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
            
            # 这里为了快速测试网页展示，我们先返回一组模拟的计算结果
            # （当你带回家部署到 Vercel 时，会由真正的 pricelib 引擎计算）
            mock_result = {
                "pv": 7.4851,
                "delta": 0.6083,
                "gamma": 0.0256,
                "vega": 0.3841,
                "theta": -0.0123,
                "rho": 0.5335
            }
            
            # 返回 200 成功状态和 JSON 数据
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(mock_result).encode('utf-8'))
        else:
            # 对于普通的 HTML/CSS/JS 文件，按默认方式处理
            super().do_POST()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), LocalDevHandler) as httpd:
        print("========================================")
        print(f"🚀 本地测试服务器已启动！")
        print(f"👉 请在浏览器中点击访问: http://localhost:{PORT}/projects/option-pricing.html")
        print("========================================\n")
        httpd.serve_forever()