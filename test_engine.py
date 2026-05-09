from pricelib import VanillaOption, CallPut, ExerciseType
import json

def test_pricing():
    print("⏳ 正在初始化 Pricelib 引擎...")
    try:
        # 模拟前端即将传过来的基础香草期权参数
        option = VanillaOption(
            s=90, 
            strike=100.0, 
            maturity=1.0, 
            r=0.03, # 3% 
            q=0.0,  # 0%
            vol=0.15, # 15%
            callput=CallPut.Call, 
            exercise_type=ExerciseType.European
        )
        
        # 调用核心计算方法
        result = option.pv_and_greeks()
        
        print("\n✅ 定价成功！输出结果如下：")
        print(json.dumps(result, indent=4, ensure_ascii=False))
        
    except Exception as e:
        print(f"\n❌ 定价失败，报错信息：{e}")

if __name__ == "__main__":
    test_pricing()