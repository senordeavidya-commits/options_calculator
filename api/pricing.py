import os
# 1. 彻底关闭 Numba JIT 编译，完美绕过 locator 报错，同时极大缩短 Vercel 冷启动时间！
os.environ["NUMBA_DISABLE_JIT"] = "1"
# 2. 双重保险：强制将缓存目录指向唯一可写的 /tmp
os.environ["NUMBA_CACHE_DIR"] = "/tmp
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

            # === 高级结构参数提取 ===
            s0 = float(params.get('s0', s))
            barrier = float(params.get('barrier', s))
            barrier_in = float(params.get('barrier_in', 80))
            barrier_out = float(params.get('barrier_out', 103))
            coupon = float(params.get('coupon', 10)) / 100.0
            lock_term = int(params.get('lock_term', 3))
            rebate = float(params.get('rebate', 1.0))
            
            # === 障碍期权特有枚举提取 ===
            inout_str = params.get('inout', 'Out')
            inout_enum = pricelib.InOut.In if 'In' in inout_str else pricelib.InOut.Out
            
            updown_str = params.get('updown', 'Up')
            updown_enum = pricelib.UpDown.Up if 'Up' in updown_str else pricelib.UpDown.Down
            
            # === 二元期权特有参数 ===
            touch_type_str = params.get('touch_type', 'Touch')
            touch_type_enum = pricelib.TouchType.Touch if 'Touch' in touch_type_str else pricelib.TouchType.NotTouch
            
            payment_type_str = params.get('payment_type', 'Expire')
            payment_type_enum = pricelib.PaymentType.Hit if 'Hit' in payment_type_str else pricelib.PaymentType.Expire

            # === 亚式期权特有参数 ===
            ave_method_str = params.get('ave_method', 'Arithmetic')
            ave_method_enum = pricelib.AverageMethod.Arithmetic if 'Arithmetic' in ave_method_str else pricelib.AverageMethod.Geometric
            
            substitute_str = params.get('substitute', 'Underlying')
            substitute_enum = pricelib.AsianAveSubstitution.Underlying if 'Underlying' in substitute_str else pricelib.AsianAveSubstitution.Strike

            # === 额外参数 ===
            leverage_ratio = float(params.get('leverage_ratio', 2))
            barrier_yield = float(params.get('barrier_yield', barrier_out))

            # 校验产品是否存在于底层库
            if not hasattr(pricelib, product_class):
                raise ValueError(f"库中找不到该产品结构: {product_class}")
            ProductClass = getattr(pricelib, product_class)

            # 核心多态路由：根据产品名称动态构建对应的 kwargs
            # === 香草期权 ===
            if product_class == 'VanillaOption':
                option = ProductClass(strike=strike, maturity=maturity, r=r, q=q, vol=vol, callput=cp_enum, exercise_type=ex_enum, s=s)
                
            # === 亚式期权 ===
            elif product_class == 'AsianOption':
                option = ProductClass(callput=cp_enum, ave_method=ave_method_enum, strike=strike, 
                                     substitute=substitute_enum, maturity=maturity, s=s, r=r, q=q, vol=vol)
                
            # === 二元期权 ===
            elif product_class == 'DigitalOption':
                option = ProductClass(strike=strike, rebate=rebate, callput=cp_enum, exercise_type=ex_enum, 
                                     payment_type=payment_type_enum, maturity=maturity, s=s, r=r, q=q, vol=vol)
                
            # === 双边二元期权 ===
            elif product_class == 'DoubleDigitalOption':
                bound = (barrier_in, barrier_out)
                option = ProductClass(touch_type=touch_type_enum, exercise_type=ex_enum, payment_type=payment_type_enum,
                                     bound=bound, rebate=(rebate, rebate), maturity=maturity, s=s, r=r, q=q, vol=vol)
                
            # === 单边障碍期权 ===
            elif product_class == 'BarrierOption':
                option = ProductClass(strike=strike, barrier=barrier, rebate=rebate, callput=cp_enum, 
                                     inout=inout_enum, updown=updown_enum, maturity=maturity, s=s, r=r, q=q, vol=vol)
                
            # === 双边障碍期权 ===
            elif product_class == 'DoubleBarrierOption':
                bound = (barrier_in, barrier_out)
                option = ProductClass(strike=strike, callput=cp_enum, inout=inout_enum, exercise_type=ex_enum,
                                     payment_type=payment_type_enum, bound=bound, rebate=(0, 0), maturity=maturity, s=s, r=r, q=q, vol=vol)
                
            # === 安全气囊 ===
            elif product_class == 'Airbag':
                option = ProductClass(strike=strike, barrier=barrier, knockin_parti=1, call_parti=0.8, 
                                     reset_call_parti=1, maturity=maturity, s=s, r=r, q=q, vol=vol)
                
            # === 双鲨期权 ===
            elif product_class == 'DoubleShark':
                strike_tuple = (min(strike, s), max(strike, s * 1.1)) if strike != 0 else (90, 110)
                bound = (barrier_in, barrier_out) if barrier_in != 0 and barrier_out != 0 else (80, 120)
                option = ProductClass(strike=strike_tuple, bound=bound, rebate=(0, 0), parti=(1, 1),
                                     maturity=maturity, s=s, r=r, q=q, vol=vol)
                
            # === 标准雪球系列（使用通用参数）===
            elif product_class == 'StandardSnowball':
                option = ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                                     coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                                     s=s, r=r, q=q, vol=vol)
                
            elif product_class == 'StepDownSnowball':
                option = ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                                     coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                                     s=s, r=r, q=q, vol=vol)
                
            elif product_class == 'OTMSnowball':
                option = ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                                     coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                                     s=s, r=r, q=q, vol=vol)
                
            elif product_class == 'SnowballPlus':
                option = ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                                     coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                                     s=s, r=r, q=q, vol=vol)
                
            elif product_class == 'FlooredSnowball':
                option = ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                                     coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                                     s=s, r=r, q=q, vol=vol)
                
            elif product_class == 'ParachuteSnowball':
                option = ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                                     coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                                     s=s, r=r, q=q, vol=vol)
                
            # === 特殊雪球（需要额外处理）===
            elif product_class == 'ParisSnowball':
                option = ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                                     coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                                     s=s, r=r, q=q, vol=vol)
                
            elif product_class == 'EarlyProfitSnowball':
                # 早利雪球需要两个票息参数
                option = ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                                     coupon_out1=coupon, coupon_out2=coupon*0.8, lock_term=lock_term, 
                                     maturity=maturity, s=s, r=r, q=q, vol=vol)
                
            elif product_class == 'ButterflySnowball':
                # 蝶变雪球需要三个票息参数
                option = ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                                     coupon_out1=coupon, coupon_out2=coupon*0.9, coupon_out3=coupon*0.8, 
                                     lock_term=lock_term, maturity=maturity, s=s, r=r, q=q, vol=vol)
                
            elif product_class == 'BothDownSnowball':
                # 双边降敲雪球需要特殊参数
                option = ProductClass(s0=s0, barrier_out_start=barrier_out, barrier_out_step=1, 
                                     barrier_in=barrier_in, coupon_ko_start=coupon, coupon_ko_step=0.01,
                                     lock_term=lock_term, maturity=maturity, s=s, r=r, q=q, vol=vol)
                
            # === FCN/DCN ===
            elif product_class == 'FCN':
                option = ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                                     coupon=coupon, lock_term=lock_term, maturity=maturity, 
                                     s=s, r=r, q=q, vol=vol)
                
            elif product_class == 'DCN':
                option = ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                                     coupon=coupon, lock_term=lock_term, maturity=maturity, 
                                     s=s, r=r, q=q, vol=vol)
                
            # === Phoenix ===
            elif product_class == 'Phoenix':
                option = ProductClass(s0=s0, barrier_out=barrier_out, barrier_yield=barrier_yield, 
                                     barrier_in=barrier_in, coupon=coupon, lock_term=lock_term, 
                                     maturity=maturity, s=s, r=r, q=q, vol=vol)
                
            # === AutoCall ===
            elif product_class == 'AutoCall':
                option = ProductClass(s0=s0, barrier_out=barrier_out, coupon_out=coupon, 
                                     coupon_div=0, lock_term=lock_term, maturity=maturity, 
                                     s=s, r=r, q=q, vol=vol)
                
            # === Accumulator ===
            elif product_class == 'Accumulator':
                option = ProductClass(s0=s0, barrier_out=barrier_out, strike=strike, 
                                     leverage_ratio=leverage_ratio, maturity=maturity, 
                                     s=s, r=r, q=q, vol=vol)
                
            # === RangeAccural ===
            elif product_class == 'RangeAccural':
                option = ProductClass(s0=s0, upper_strike=barrier_out, lower_strike=barrier_in, 
                                     payment=coupon, maturity=maturity, s=s, r=r, q=q, vol=vol)
                
            else:
                raise ValueError(f"系统网关暂未配置此产品类型的参数路由: {product_class}")
            
            # 动态引擎注入
            if engine_id:
                if not hasattr(pricelib, engine_id):
                    raise ValueError(f"底层库不存在此定价引擎: {engine_id}")
                EngineClass = getattr(pricelib, engine_id)
                engine = EngineClass(s=s, r=r, q=q, vol=vol)
                option.set_pricing_engine(engine)
            
            # 执行定价计算
            result = option.pv_and_greeks()

            # 构建安全响应
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
