# 单元测试骨架（可自行修改）

## 运行方式

在项目根目录执行：

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

也可以单独跑某个文件：

```powershell
python -m unittest tests.test_scoring -v
python -m unittest tests.test_matchmaking -v
```

## 可以直接改的地方

1. `tests/test_matchmaking.py` 中的 `_sample_data()`  
改成真实比赛的办公室、队名、队员、等级分布。

2. `tests/test_scoring.py` 中的输入样例  
把 `"14" / "10"` 等等级改成实际想覆盖的边界情况。

3. 新增
例如：某轮某队必须出现一次、平局必须有获胜方等。

## 说明

这套测试是“骨架”，不依赖数据库，不会改动生产数据。
