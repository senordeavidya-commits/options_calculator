import os
os.environ["NUMBA_DISABLE_JIT"] = "1"
os.environ["NUMBA_CACHE_DIR"] = "/tmp"

from http.server import BaseHTTPRequestHandler
import json
import traceback
import pricelib

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")
        self.end_headers()

    def do_GET(self):
        self._handle_request()
    
    def do_POST(self):
        self._handle_request()
    
    def _handle_request(self):
        try:
            # 构建产品参数映射
            products = {
                # === 香草期权 ===
                "VanillaOption": {
                    "name_zh": "欧式/美式香草期权",
                    "supported_engines": ["AnalyticVanillaEuEngine", "AnalyticVanillaAmEngine", "MCVanillaEngine", 
                                         "FdmVanillaEngine", "QuadVanillaEngine", "BiTreeVanillaEngine"],
                    "required_params": ["s", "strike", "maturity", "r", "q", "vol", "callput", "subCategory"],
                    "ui": {"hideStrike": False, "hideCallput": False, "hideExercise": False}
                },
                
                # === 亚式期权 ===
                "AsianOption": {
                    "name_zh": "亚式期权",
                    "supported_engines": ["AnalyticAsianEngine", "MCAsianEngine", "BiTreeAsianEngine"],
                    "required_params": ["s", "strike", "maturity", "r", "q", "vol", "callput"],
                    "ui": {"hideStrike": False, "hideCallput": False, "hideExercise": True}
                },
                
                # === 二元期权 ===
                "DigitalOption": {
                    "name_zh": "二元期权",
                    "supported_engines": ["AnalyticCashOrNothingEngine", "MCDigitalEngine", 
                                         "FdmDigitalEngine", "QuadDigitalEngine", "BiTreeDigitalEngine"],
                    "required_params": ["s", "strike", "maturity", "r", "q", "vol", "callput", "rebate"],
                    "ui": {"hideStrike": False, "hideCallput": False, "hideExercise": True}
                },
                
                # === 双边二元期权 ===
                "DoubleDigitalOption": {
                    "name_zh": "双边二元期权",
                    "supported_engines": ["MCDoubleDigitalEngine", "FdmDigitalEngine", "AnalyticDoubleDigitalEngine"],
                    "required_params": ["s", "maturity", "r", "q", "vol", "barrier_in", "barrier_out"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === 单边障碍期权 ===
                "BarrierOption": {
                    "name_zh": "单障碍期权",
                    "supported_engines": ["AnalyticBarrierEngine", "MCBarrierEngine", 
                                         "FdmBarrierEngine", "QuadBarrierEngine", "BiTreeBarrierEngine"],
                    "required_params": ["s", "strike", "maturity", "r", "q", "vol", "callput", 
                                       "barrier", "inout", "updown"],
                    "ui": {"hideStrike": False, "hideCallput": False, "hideExercise": True}
                },
                
                # === 双边障碍期权 ===
                "DoubleBarrierOption": {
                    "name_zh": "双边障碍期权",
                    "supported_engines": ["AnalyticDoubleBarrierEngine", "MCDoubleBarrierEngine"],
                    "required_params": ["s", "strike", "maturity", "r", "q", "vol", "callput", 
                                       "barrier_in", "barrier_out", "inout"],
                    "ui": {"hideStrike": False, "hideCallput": False, "hideExercise": True}
                },
                
                # === 安全气囊 ===
                "Airbag": {
                    "name_zh": "安全气囊期权",
                    "supported_engines": ["AnalyticAirbagEngine", "MCAirbagEngine", "FdmAirbagEngine"],
                    "required_params": ["s", "strike", "maturity", "r", "q", "vol", "barrier"],
                    "ui": {"hideStrike": False, "hideCallput": True, "hideExercise": True}
                },
                
                # === 双鲨期权 ===
                "DoubleShark": {
                    "name_zh": "双鲨期权",
                    "supported_engines": ["FdmDoubleSharkEngine", "MCDoubleSharkEngine", "QuadDoubleSharkEngine"],
                    "required_params": ["s", "maturity", "r", "q", "vol", "barrier_in", "barrier_out"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === 标准雪球 ===
                "StandardSnowball": {
                    "name_zh": "经典雪球",
                    "supported_engines": ["MCAutoCallableEngine", "FdmSnowBallEngine", "QuadSnowballEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_in", "barrier_out", "coupon", "lock_term"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === 降敲雪球 ===
                "StepDownSnowball": {
                    "name_zh": "降敲雪球",
                    "supported_engines": ["MCAutoCallableEngine", "FdmSnowBallEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_in", "barrier_out", "coupon", "lock_term"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === OTM雪球 ===
                "OTMSnowball": {
                    "name_zh": "OTM雪球",
                    "supported_engines": ["MCAutoCallableEngine", "FdmSnowBallEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_in", "barrier_out", "coupon", "lock_term"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === 雪球增强 ===
                "SnowballPlus": {
                    "name_zh": "雪球增强",
                    "supported_engines": ["MCAutoCallableEngine", "FdmSnowBallEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_in", "barrier_out", "coupon", "lock_term"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === 保底雪球 ===
                "FlooredSnowball": {
                    "name_zh": "保底雪球",
                    "supported_engines": ["MCAutoCallableEngine", "FdmSnowBallEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_in", "barrier_out", "coupon", "lock_term"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === 降落伞雪球 ===
                "ParachuteSnowball": {
                    "name_zh": "降落伞雪球",
                    "supported_engines": ["MCAutoCallableEngine", "FdmSnowBallEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_in", "barrier_out", "coupon", "lock_term"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === 巴黎雪球 ===
                "ParisSnowball": {
                    "name_zh": "巴黎雪球",
                    "supported_engines": ["MCParisSnowballEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_in", "barrier_out", "coupon", "lock_term"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === 早利雪球 ===
                "EarlyProfitSnowball": {
                    "name_zh": "早利雪球",
                    "supported_engines": ["MCAutoCallableEngine", "FdmSnowBallEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_in", "barrier_out", "coupon", "lock_term"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === 蝶变雪球 ===
                "ButterflySnowball": {
                    "name_zh": "蝶变雪球",
                    "supported_engines": ["MCAutoCallableEngine", "FdmSnowBallEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_in", "barrier_out", "coupon", "lock_term"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === 双边降敲雪球 ===
                "BothDownSnowball": {
                    "name_zh": "双边降敲雪球",
                    "supported_engines": ["MCAutoCallableEngine", "FdmSnowBallEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_in", "barrier_out", "coupon", "lock_term"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === FCN ===
                "FCN": {
                    "name_zh": "定期派息票据",
                    "supported_engines": ["QuadFCNEngine", "MCPhoenixEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_in", "barrier_out", "coupon", "lock_term"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === DCN ===
                "DCN": {
                    "name_zh": "数字看涨票据",
                    "supported_engines": ["MCPhoenixEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_in", "barrier_out", "coupon", "lock_term"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === Phoenix ===
                "Phoenix": {
                    "name_zh": "凤凰票据",
                    "supported_engines": ["MCPhoenixEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_in", "barrier_out", "coupon", "lock_term"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === AutoCall ===
                "AutoCall": {
                    "name_zh": "自动赎回",
                    "supported_engines": ["MCAutoCallableEngine", "QuadAutoCallEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_out", "coupon", "lock_term"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                },
                
                # === Accumulator ===
                "Accumulator": {
                    "name_zh": "累计期权",
                    "supported_engines": ["MCAccumulatorEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "strike", "barrier_out", "leverage_ratio"],
                    "ui": {"hideStrike": False, "hideCallput": True, "hideExercise": True}
                },
                
                # === RangeAccural ===
                "RangeAccural": {
                    "name_zh": "区间累计期权",
                    "supported_engines": ["MCRangeAccuralEngine"],
                    "required_params": ["s", "s0", "maturity", "r", "q", "vol", 
                                       "barrier_in", "barrier_out", "coupon"],
                    "ui": {"hideStrike": True, "hideCallput": True, "hideExercise": True}
                }
            }
            
            # 枚举类型定义
            enums = {
                "callput": ["Call", "Put"],
                "inout": ["In", "Out"],
                "updown": ["Up", "Down"],
                "subCategory": ["European", "American"],
                "payment_type": ["Hit", "Expire"],
                "touch_type": ["Touch", "NotTouch"],
                "ave_method": ["Arithmetic", "Geometric"],
                "substitute": ["Underlying", "Strike"]
            }
            
            # 参数元信息（用于前端渲染）
            params_meta = {
                "s": {"name": "标的价格", "unit": "", "type": "number", "default": 100, "min": 0.1},
                "s0": {"name": "初始价格", "unit": "", "type": "number", "default": 100, "min": 0.1},
                "strike": {"name": "执行价格", "unit": "", "type": "number", "default": 100, "min": 0.1},
                "maturity": {"name": "到期期限", "unit": "年", "type": "number", "default": 1, "min": 0.01},
                "r": {"name": "无风险利率", "unit": "%", "type": "number", "default": 3, "min": 0, "max": 100},
                "q": {"name": "分红/融券率", "unit": "%", "type": "number", "default": 0, "min": 0, "max": 100},
                "vol": {"name": "波动率", "unit": "%", "type": "number", "default": 15, "min": 0.1, "max": 100},
                "callput": {"name": "期权类型", "unit": "", "type": "enum", "options": ["Call", "Put"]},
                "subCategory": {"name": "行权方式", "unit": "", "type": "enum", "options": ["European", "American"]},
                "barrier": {"name": "障碍价格", "unit": "", "type": "number", "default": 100, "min": 0.1},
                "barrier_in": {"name": "敲入障碍", "unit": "", "type": "number", "default": 80, "min": 0.1},
                "barrier_out": {"name": "敲出障碍", "unit": "", "type": "number", "default": 103, "min": 0.1},
                "coupon": {"name": "票息率", "unit": "%", "type": "number", "default": 10, "min": 0, "max": 100},
                "lock_term": {"name": "锁定期", "unit": "月", "type": "integer", "default": 3, "min": 0},
                "rebate": {"name": "赔付金额", "unit": "", "type": "number", "default": 1.0, "min": 0},
                "inout": {"name": "敲入/敲出", "unit": "", "type": "enum", "options": ["In", "Out"]},
                "updown": {"name": "向上/向下", "unit": "", "type": "enum", "options": ["Up", "Down"]},
                "payment_type": {"name": "支付方式", "unit": "", "type": "enum", "options": ["Hit", "Expire"]},
                "touch_type": {"name": "触碰类型", "unit": "", "type": "enum", "options": ["Touch", "NotTouch"]},
                "ave_method": {"name": "平均方式", "unit": "", "type": "enum", "options": ["Arithmetic", "Geometric"]},
                "substitute": {"name": "替代方式", "unit": "", "type": "enum", "options": ["Underlying", "Strike"]},
                "leverage_ratio": {"name": "杠杆倍数", "unit": "", "type": "number", "default": 2, "min": 1}
            }
            
            response_data = {
                "code": 0,
                "data": {
                    "products": products,
                    "enums": enums,
                    "params_meta": params_meta
                }
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
            
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
