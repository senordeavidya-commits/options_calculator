from http.server import BaseHTTPRequestHandler
import json
import traceback
import pricelib

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = json.loads(post_data)

            # 1. 基础市场参数解析
            s = float(params.get('s', 100))
            strike = float(params.get('strike', 100))
            maturity = float(params.get('maturity', 1))
            r = float(params.get('r', 3)) / 100.0  
            q = float(params.get('q', 0)) / 100.0   
            vol = float(params.get('vol', 15)) / 100.0  
            
            # 2. 解析 Enum 映射 (直接从 pricelib 模块获取，防止 Import 失败)
            callput_str = params.get('callput', 'Call')
            cp_enum = pricelib.CallPut.Call if 'Call' in callput_str else pricelib.CallPut.Put

            subcategory_str = params.get('subCategory', 'European')
            ex_enum = pricelib.ExerciseType.American if 'American' in subcategory_str or '美式' in subcategory_str else pricelib.ExerciseType.European

            product_class = params.get('product_class', 'VanillaOption')
            engine_id = params.get('engine_id', '')

            # 3. 懒加载：根据产品类型动态实例化 (只算你需要的那一个)
            if product_class == 'VanillaOption':
                option = pricelib.VanillaOption(
                    s=s, strike=strike, maturity=maturity,
                    r=r, q=q, vol=vol,
                    callput=cp_enum, exercise_type=ex_enum
                )
            elif 'Snowball' in product_class:
                # 动态处理雪球类产品
                s0 = float(params.get('s0', s))
                barrier_in = float(params.get('barrier_in', 0))
                barrier_out = float(params.get('barrier_out', 0))
                coupon = float(params.get('coupon', 0)) / 100.0
                lock_term = int(params.get('lock_term', 0))
                
                # 动态获取对应的雪球类
                if not hasattr(pricelib, product_class):
                    raise ValueError(f"库中找不到该雪球结构: {product_class}")
                ProductClass = getattr(pricelib, product_class)
                option = ProductClass(
                    s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                    coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                    s=s, r=r, q=q, vol=vol
                )
            else:
                # 如果是你还没在前端做好参数对应的新奇期权，优雅地报错
                raise ValueError(f"系统网关暂未配置此产品类型的参数路由: {product_class}")
            
            # 4. 动态引擎注入 (极其优雅的反射机制)
            if engine_id:
                if not hasattr(pricelib, engine_id):
                    raise ValueError(f"底层库不存在此定价引擎: {engine_id}")
                # 动态抓取引擎类并实例化
                EngineClass = getattr(pricelib, engine_id)
                engine = EngineClass(s=s, r=r, q=q, vol=vol)
                option.set_pricing_engine(engine)
            
            # 5. 执行定价计算
            result = option.pv_and_greeks()

            # 6. 构建安全响应
            response_data = {
                "code": 0,
                "data": {
                    "pv": result.get("pv", 0),
                    "greeks": {
                        "delta": result.get("delta", 0),
                        "gamma": result.get("gamma", 0),
                        "vega": result.get("vega", 0),
                        "theta": result.get("theta", 0),
                        "rho": result.get("rho", 0)
                    }
                }
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            # 终极护盾：哪怕底层算爆了，前端也能收到绿色的 200 和红色的报错提示，绝不 500 崩溃
            error_trace = traceback.format_exc()
            self.send_response(200) 
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                "code": -1,
                "msg": str(e),
                "trace": error_trace 
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
