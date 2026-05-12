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
            request_data = json.loads(post_data)
            
            params = request_data.get('params', {})
            matrix_config = request_data.get('matrix_config', {})
            
            # 解析矩阵配置
            x_param = matrix_config.get('x_param', 's')
            x_min = float(matrix_config.get('x_min', 90))
            x_max = float(matrix_config.get('x_max', 110))
            x_steps = int(matrix_config.get('x_steps', 10))
            
            y_param = matrix_config.get('y_param', 'vol')
            y_min = float(matrix_config.get('y_min', 10))
            y_max = float(matrix_config.get('y_max', 30))
            y_steps = int(matrix_config.get('y_steps', 10))
            
            target_value = matrix_config.get('target_value', 'pv')
            
            # 安全检查：防止计算量过大
            total_iterations = x_steps * y_steps
            if total_iterations > 400:
                raise ValueError(f"计算量过大 ({total_iterations} > 400)，请减少步数")
            
            # 1. 基础市场参数解析
            s = float(params.get('s', 100))
            strike = float(params.get('strike', 100))
            maturity = float(params.get('maturity', 1))
            r = float(params.get('r', 3)) / 100.0  
            q = float(params.get('q', 0)) / 100.0   
            vol = float(params.get('vol', 15)) / 100.0  
            
            # 2. 解析 Enum 映射
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
            option = self._create_option(
                product_class, ProductClass,
                s, strike, maturity, r, q, vol, cp_enum, ex_enum,
                s0, barrier, barrier_in, barrier_out, coupon, lock_term, rebate,
                inout_enum, updown_enum, touch_type_enum, payment_type_enum,
                ave_method_enum, substitute_enum, leverage_ratio, barrier_yield
            )

            # 动态引擎注入
            if engine_id:
                if not hasattr(pricelib, engine_id):
                    raise ValueError(f"底层库不存在此定价引擎: {engine_id}")
                EngineClass = getattr(pricelib, engine_id)
                base_engine = EngineClass(s=s, r=r, q=q, vol=vol)
                option.set_pricing_engine(base_engine)
            
            # 生成坐标轴序列
            x_values = self._generate_range(x_min, x_max, x_steps)
            y_values = self._generate_range(y_min, y_max, y_steps)
            
            # 判断是否需要百分比换算
            x_is_percent = x_param in ['vol', 'r', 'q', 'coupon']
            y_is_percent = y_param in ['vol', 'r', 'q', 'coupon']
            
            # 执行矩阵计算
            matrix_data = []
            for y_val in y_values:
                row = []
                for x_val in x_values:
                    # 创建新引擎实例，设置当前坐标值
                    current_s = x_val if x_param == 's' else s
                    current_vol = (x_val / 100.0) if x_param == 'vol' else vol
                    current_r = (x_val / 100.0) if x_param == 'r' else r
                    current_q = (x_val / 100.0) if x_param == 'q' else q
                    
                    current_vol_y = (y_val / 100.0) if y_param == 'vol' else current_vol
                    current_r_y = (y_val / 100.0) if y_param == 'r' else current_r
                    current_q_y = (y_val / 100.0) if y_param == 'q' else current_q
                    
                    # 重新实例化引擎
                    if engine_id:
                        EngineClass = getattr(pricelib, engine_id)
                        current_engine = EngineClass(s=current_s, r=current_r_y, q=current_q_y, vol=current_vol_y)
                        option.set_pricing_engine(current_engine)
                    
                    # 更新期权的 s 属性（如果期权有这个属性）
                    if hasattr(option, 's'):
                        option.s = current_s
                    
                    result = option.pv_and_greeks()
                    
                    # 获取目标值
                    if target_value == 'pv':
                        val = result.get('pv', 0)
                    elif target_value in ['delta', 'gamma', 'vega', 'theta', 'rho']:
                        val = result.get('greeks', {}).get(target_value, 0)
                    else:
                        val = result.get(target_value, 0)
                    
                    row.append(val)
                matrix_data.append(row)
            
            # 构建响应
            response_data = {
                "code": 0,
                "data": {
                    "matrix": matrix_data,
                    "x_axis": x_values,
                    "y_axis": y_values,
                    "x_param": x_param,
                    "y_param": y_param,
                    "target_value": target_value
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
    
    def _create_option(self, product_class, ProductClass,
                       s, strike, maturity, r, q, vol, cp_enum, ex_enum,
                       s0, barrier, barrier_in, barrier_out, coupon, lock_term, rebate,
                       inout_enum, updown_enum, touch_type_enum, payment_type_enum,
                       ave_method_enum, substitute_enum, leverage_ratio, barrier_yield):
        """创建期权对象的辅助方法"""
        if product_class == 'VanillaOption':
            return ProductClass(strike=strike, maturity=maturity, r=r, q=q, vol=vol, callput=cp_enum, exercise_type=ex_enum, s=s)
        
        elif product_class == 'AsianOption':
            return ProductClass(callput=cp_enum, ave_method=ave_method_enum, strike=strike, 
                               substitute=substitute_enum, maturity=maturity, s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'DigitalOption':
            return ProductClass(strike=strike, rebate=rebate, callput=cp_enum, exercise_type=ex_enum, 
                               payment_type=payment_type_enum, maturity=maturity, s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'DoubleDigitalOption':
            bound = (barrier_in, barrier_out)
            return ProductClass(touch_type=touch_type_enum, exercise_type=ex_enum, payment_type=payment_type_enum,
                               bound=bound, rebate=(rebate, rebate), maturity=maturity, s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'BarrierOption':
            return ProductClass(strike=strike, barrier=barrier, rebate=rebate, callput=cp_enum, 
                               inout=inout_enum, updown=updown_enum, maturity=maturity, s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'DoubleBarrierOption':
            bound = (barrier_in, barrier_out)
            return ProductClass(strike=strike, callput=cp_enum, inout=inout_enum, exercise_type=ex_enum,
                               payment_type=payment_type_enum, bound=bound, rebate=(0, 0), maturity=maturity, s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'Airbag':
            return ProductClass(strike=strike, barrier=barrier, knockin_parti=1, call_parti=0.8, 
                               reset_call_parti=1, maturity=maturity, s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'DoubleShark':
            strike_tuple = (min(strike, s), max(strike, s * 1.1)) if strike != 0 else (90, 110)
            bound = (barrier_in, barrier_out) if barrier_in != 0 and barrier_out != 0 else (80, 120)
            return ProductClass(strike=strike_tuple, bound=bound, rebate=(0, 0), parti=(1, 1),
                               maturity=maturity, s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'StandardSnowball':
            return ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                               coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                               s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'StepDownSnowball':
            return ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                               coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                               s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'OTMSnowball':
            return ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                               coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                               s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'SnowballPlus':
            return ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                               coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                               s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'FlooredSnowball':
            return ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                               coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                               s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'ParachuteSnowball':
            return ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                               coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                               s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'ParisSnowball':
            return ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                               coupon_out=coupon, lock_term=lock_term, maturity=maturity, 
                               s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'EarlyProfitSnowball':
            return ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                               coupon_out1=coupon, coupon_out2=coupon*0.8, lock_term=lock_term, 
                               maturity=maturity, s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'ButterflySnowball':
            return ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                               coupon_out1=coupon, coupon_out2=coupon*0.9, coupon_out3=coupon*0.8, 
                               lock_term=lock_term, maturity=maturity, s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'BothDownSnowball':
            return ProductClass(s0=s0, barrier_out_start=barrier_out, barrier_out_step=1, 
                               barrier_in=barrier_in, coupon_ko_start=coupon, coupon_ko_step=0.01,
                               lock_term=lock_term, maturity=maturity, s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'FCN':
            return ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                               coupon=coupon, lock_term=lock_term, maturity=maturity, 
                               s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'DCN':
            return ProductClass(s0=s0, barrier_out=barrier_out, barrier_in=barrier_in, 
                               coupon=coupon, lock_term=lock_term, maturity=maturity, 
                               s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'Phoenix':
            return ProductClass(s0=s0, barrier_out=barrier_out, barrier_yield=barrier_yield, 
                               barrier_in=barrier_in, coupon=coupon, lock_term=lock_term, 
                               maturity=maturity, s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'AutoCall':
            return ProductClass(s0=s0, barrier_out=barrier_out, coupon_out=coupon, 
                               coupon_div=0, lock_term=lock_term, maturity=maturity, 
                               s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'Accumulator':
            return ProductClass(s0=s0, barrier_out=barrier_out, strike=strike, 
                               leverage_ratio=leverage_ratio, maturity=maturity, 
                               s=s, r=r, q=q, vol=vol)
        
        elif product_class == 'RangeAccural':
            return ProductClass(s0=s0, upper_strike=barrier_out, lower_strike=barrier_in, 
                               payment=coupon, maturity=maturity, s=s, r=r, q=q, vol=vol)
        
        else:
            raise ValueError(f"系统网关暂未配置此产品类型的参数路由: {product_class}")
    
    def _generate_range(self, min_val, max_val, steps):
        """生成均匀分布的数值序列"""
        if steps <= 1:
            return [min_val]
        step_size = (max_val - min_val) / (steps - 1)
        return [min_val + i * step_size for i in range(steps)]
