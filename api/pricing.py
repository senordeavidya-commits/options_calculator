from http.server import BaseHTTPRequestHandler
import json
import urllib.parse

from pricelib import (
    VanillaOption, CallPut, ExerciseType,
    StandardSnowball, StepdownSnowball, EarlyProfitSnowball, ButterflySnowball, ParisSnowball,
    BarrierOption, DoubleBarrierOption, Airbag,
    AsianOption, DigitalOption, DoubleDigitalOption,
    Accumulator, RangeAccural,
    FCN, Phoenix,
    InOut, UpDown,
    AnalyticVanillaEuEngine, AnalyticVanillaAmEngine,
    FdmVanillaEngine, MCVanillaEngine, QuadVanillaEngine, BiTreeVanillaEngine,
    FdmSnowBallEngine, MCAutoCallableEngine, QuadSnowballEngine,
    AnalyticBarrierEngine, FdmBarrierEngine, MCBarrierEngine, QuadBarrierEngine, BiTreeBarrierEngine,
    AnalyticAirbagEngine, FdmAirbagEngine, MCAirbagEngine,
    AnalyticAsianEngine, BiTreeAsianEngine, MCAsianEngine,
    AnalyticDigitalEngine, FdmDigitalEngine, MCDigitalEngine, QuadDigitalEngine, BiTreeDigitalEngine,
    MCAccumulator, MCRangeAccural,
    QuadFcnEngine, MCPhoenixEngine
)

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

            # 动态提取通用参数（使用安全的 .get() 方法并转换类型）
            s = float(params.get('s', 0))
            strike = float(params.get('strike', 0))
            maturity = float(params.get('maturity', 0))
            r = float(params.get('r', 0)) / 100.0  # 前端传的是百分比
            q = float(params.get('q', 0)) / 100.0   # 前端传的是百分比
            vol = float(params.get('vol', 0)) / 100.0  # 前端传的是百分比
            
            # 解析期权类型和行权方式
            callput_str = params.get('callput', 'Call')
            exercise_type_str = params.get('exercise_type', 'European')
            product_class = params.get('product_class', 'VanillaOption')
            engine_id = params.get('engine_id', '')
            
            callput_enum = CallPut.Call if callput_str == "Call" else CallPut.Put
            exercise_type_enum = ExerciseType.European if exercise_type_str == "European" else ExerciseType.American

            # 动态创建产品对象
            option = self.create_product(
                product_class,
                s=s, strike=strike, maturity=maturity,
                r=r, q=q, vol=vol,
                callput=callput_enum, exercise_type=exercise_type_enum,
                params=params
            )
            
            # 根据engine_id设置定价引擎（如果提供）
            if engine_id:
                engine = self.create_engine(engine_id, s=s, r=r, q=q, vol=vol)
                if engine:
                    option.set_pricing_engine(engine)
            
            # 执行定价计算
            result = option.pv_and_greeks()

            # 构建响应数据
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
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"code": -1, "msg": str(e)}).encode('utf-8'))

    def create_product(self, product_class, **kwargs):
        """动态创建产品对象"""
        params = kwargs.pop('params', {})
        s = kwargs.get('s')
        strike = kwargs.get('strike')
        maturity = kwargs.get('maturity')
        r = kwargs.get('r')
        q = kwargs.get('q')
        vol = kwargs.get('vol')
        callput = kwargs.get('callput')
        exercise_type = kwargs.get('exercise_type')
        
        # 雪球结构参数
        s0 = float(params.get('s0', s))
        barrier_in = float(params.get('barrier_in', 0))
        barrier_out = float(params.get('barrier_out', 0))
        coupon = float(params.get('coupon', 0)) / 100.0  # 前端传的是百分比
        lock_term = int(params.get('lock_term', 0))
        
        # 障碍期权参数
        barrier = float(params.get('barrier', 0))
        
        # 根据产品类型创建对应的产品对象
        product_map = {
            'VanillaOption': VanillaOption(
                strike=strike,
                maturity=maturity,
                callput=callput,
                exercise_type=exercise_type,
                s=s, r=r, q=q, vol=vol
            ),
            'StandardSnowball': StandardSnowball(
                s0=s0,
                barrier_out=barrier_out,
                barrier_in=barrier_in,
                coupon_out=coupon,
                lock_term=lock_term,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
            'StepdownSnowball': StepdownSnowball(
                s0=s0,
                barrier_out=barrier_out,
                barrier_in=barrier_in,
                coupon_out=coupon,
                lock_term=lock_term,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
            'EarlyProfitSnowball': EarlyProfitSnowball(
                s0=s0,
                barrier_out=barrier_out,
                barrier_in=barrier_in,
                coupon_out=coupon,
                lock_term=lock_term,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
            'ButterflySnowball': ButterflySnowball(
                s0=s0,
                barrier_out=barrier_out,
                barrier_in=barrier_in,
                coupon_out=coupon,
                lock_term=lock_term,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
            'ParisSnowball': ParisSnowball(
                s0=s0,
                barrier_out=barrier_out,
                barrier_in=barrier_in,
                coupon_out=coupon,
                lock_term=lock_term,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
            'BarrierOption': BarrierOption(
                strike=strike,
                barrier=barrier,
                rebate=0,
                callput=callput,
                inout=InOut.Out,
                updown=UpDown.Up,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
            'DoubleBarrierOption': DoubleBarrierOption(
                strike=strike,
                barrier_lower=barrier_in,
                barrier_upper=barrier_out,
                rebate_lower=0,
                rebate_upper=0,
                callput=callput,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
            'Airbag': Airbag(
                strike=strike,
                barrier=barrier,
                callput=callput,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
            'AsianOption': AsianOption(
                strike=strike,
                callput=callput,
                exercise_type=exercise_type,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
            'DigitalOption': DigitalOption(
                strike=strike,
                callput=callput,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
            'DoubleDigitalOption': DoubleDigitalOption(
                strike_lower=barrier_in,
                strike_upper=barrier_out,
                callput=callput,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
            'Accumulator': Accumulator(
                s0=s,
                callput=callput,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
            'RangeAccural': RangeAccural(
                s0=s,
                barrier_lower=barrier_in,
                barrier_upper=barrier_out,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
            'FCN': FCN(
                s0=s,
                coupon_rate=coupon,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
            'Phoenix': Phoenix(
                s0=s,
                coupon_rate=coupon,
                maturity=maturity,
                s=s, r=r, q=q, vol=vol
            ),
        }
        
        return product_map.get(product_class, product_map['VanillaOption'])

    def create_engine(self, engine_id, **kwargs):
        """根据engine_id创建定价引擎"""
        s = kwargs.get('s')
        r = kwargs.get('r')
        q = kwargs.get('q')
        vol = kwargs.get('vol')
        
        engine_map = {
            # 香草期权引擎
            'AnalyticVanillaEuEngine': AnalyticVanillaEuEngine(s=s, r=r, q=q, vol=vol),
            'AnalyticVanillaAmEngine': AnalyticVanillaAmEngine(s=s, r=r, q=q, vol=vol),
            'FdmVanillaEngine': FdmVanillaEngine(s=s, r=r, q=q, vol=vol),
            'MCVanillaEngine': MCVanillaEngine(s=s, r=r, q=q, vol=vol),
            'QuadVanillaEngine': QuadVanillaEngine(s=s, r=r, q=q, vol=vol),
            'BiTreeVanillaEngine': BiTreeVanillaEngine(s=s, r=r, q=q, vol=vol),
            
            # 雪球引擎
            'FdmSnowBallEngine': FdmSnowBallEngine(s=s, r=r, q=q, vol=vol),
            'MCAutoCallableEngine': MCAutoCallableEngine(s=s, r=r, q=q, vol=vol),
            'QuadSnowballEngine': QuadSnowballEngine(s=s, r=r, q=q, vol=vol),
            'MCParisSnowballEngine': MCPhoenixEngine(s=s, r=r, q=q, vol=vol),
            
            # 障碍期权引擎
            'AnalyticBarrierEngine': AnalyticBarrierEngine(s=s, r=r, q=q, vol=vol),
            'FdmBarrierEngine': FdmBarrierEngine(s=s, r=r, q=q, vol=vol),
            'MCBarrierEngine': MCBarrierEngine(s=s, r=r, q=q, vol=vol),
            'QuadBarrierEngine': QuadBarrierEngine(s=s, r=r, q=q, vol=vol),
            'BiTreeBarrierEngine': BiTreeBarrierEngine(s=s, r=r, q=q, vol=vol),
            
            # 安全气囊引擎
            'AnalyticAirbagEngine': AnalyticAirbagEngine(s=s, r=r, q=q, vol=vol),
            'FdmAirbagEngine': FdmAirbagEngine(s=s, r=r, q=q, vol=vol),
            'MCAirbagEngine': MCAirbagEngine(s=s, r=r, q=q, vol=vol),
            
            # 亚式期权引擎
            'AnalyticAsianEngine': AnalyticAsianEngine(s=s, r=r, q=q, vol=vol),
            'BiTreeAsianEngine': BiTreeAsianEngine(s=s, r=r, q=q, vol=vol),
            'MCAsianEngine': MCAsianEngine(s=s, r=r, q=q, vol=vol),
            
            # 二元期权引擎
            'AnalyticDigitalEngine': AnalyticDigitalEngine(s=s, r=r, q=q, vol=vol),
            'FdmDigitalEngine': FdmDigitalEngine(s=s, r=r, q=q, vol=vol),
            'MCDigitalEngine': MCDigitalEngine(s=s, r=r, q=q, vol=vol),
            'QuadDigitalEngine': QuadDigitalEngine(s=s, r=r, q=q, vol=vol),
            'BiTreeDigitalEngine': BiTreeDigitalEngine(s=s, r=r, q=q, vol=vol),
            
            # 累计期权引擎
            'MCAccumulator': MCAccumulator(s=s, r=r, q=q, vol=vol),
            'MCRangeAccural': MCRangeAccural(s=s, r=r, q=q, vol=vol),
            
            # FCN引擎
            'QuadFcnEngine': QuadFcnEngine(s=s, r=r, q=q, vol=vol),
            
            # Phoenix引擎
            'MCPhoenixEngine': MCPhoenixEngine(s=s, r=r, q=q, vol=vol),
        }
        
        return engine_map.get(engine_id)
