"""
Calculator Tool - 計算機ツール

数学計算、単位変換、統計計算などを実行するツール
"""

import math
import re
from typing import Dict, Any, List
from loguru import logger

from src.core.tool_base import Tool, ToolResult, ToolParameter


class CalculatorTool(Tool):
    """数学計算を実行するツール"""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "数学計算、単位変換、統計計算などを実行します"

    @property
    def category(self) -> str:
        return "utility"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="expression",
                type="string",
                description="計算式（例：2+3*4, sqrt(16), sin(30)）",
                required=True
            ),
            ToolParameter(
                name="unit_conversion",
                type="string",
                description="単位変換（例：100cm to m, 32F to C）",
                required=False
            )
        ]

    async def _initialize_impl(self):
        """計算機ツールの初期化"""
        # 安全な数学関数のホワイトリスト
        self.safe_functions = {
            # 基本的な数学関数
            'abs': abs, 'round': round, 'min': min, 'max': max,
            'sum': sum, 'pow': pow,

            # math モジュールの関数
            'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
            'log': math.log, 'log10': math.log10, 'exp': math.exp,
            'floor': math.floor, 'ceil': math.ceil,
            'degrees': math.degrees, 'radians': math.radians,

            # 定数
            'pi': math.pi, 'e': math.e
        }

        # 単位変換テーブル
        self.unit_conversions = {
            # 長さ
            'length': {
                'mm': 0.001, 'cm': 0.01, 'm': 1.0, 'km': 1000,
                'inch': 0.0254, 'ft': 0.3048, 'yard': 0.9144, 'mile': 1609.34
            },
            # 重量
            'weight': {
                'mg': 0.000001, 'g': 0.001, 'kg': 1.0, 't': 1000,
                'oz': 0.0283495, 'lb': 0.453592
            },
            # 温度（特別処理）
            'temperature': {
                'celsius': 'C', 'fahrenheit': 'F', 'kelvin': 'K'
            },
            # 時間
            'time': {
                'ms': 0.001, 's': 1.0, 'min': 60, 'h': 3600,
                'day': 86400, 'week': 604800
            }
        }

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """計算を実行して結果を返す"""
        try:
            expression = parameters.get("expression", "").strip()
            unit_conversion = parameters.get("unit_conversion", "").strip()

            if not expression and not unit_conversion:
                return ToolResult(
                    success=False,
                    result=None,
                    error="計算式または単位変換が指定されていません"
                )

            result_text = ""

            # 単位変換が指定されている場合
            if unit_conversion:
                conversion_result = await self._handle_unit_conversion(unit_conversion)
                result_text += conversion_result + "\n"

            # 数学式の計算が指定されている場合
            if expression:
                calc_result = await self._calculate_expression(expression)
                result_text += calc_result

            return ToolResult(
                success=True,
                result=result_text.strip(),
                metadata={
                    "expression": expression,
                    "unit_conversion": unit_conversion
                }
            )

        except Exception as e:
            logger.error(f"Calculator tool execution failed: {e}")
            return ToolResult(
                success=False,
                result=None,
                error=f"計算の実行に失敗しました: {str(e)}"
            )

    async def _calculate_expression(self, expression: str) -> str:
        """数学式を計算"""
        try:
            # 危険な関数や構文をチェック
            if not self._is_safe_expression(expression):
                return "エラー: 安全でない計算式が検出されました"

            # 式を前処理（三角関数の度数対応など）
            processed_expr = self._preprocess_expression(expression)

            # 安全な環境で計算実行
            safe_dict = {"__builtins__": {}}
            safe_dict.update(self.safe_functions)

            result = eval(processed_expr, safe_dict, {})

            # 結果の整形
            if isinstance(result, (int, float)):
                if result == int(result):
                    formatted_result = str(int(result))
                else:
                    formatted_result = f"{result:.6f}".rstrip('0').rstrip('.')
            else:
                formatted_result = str(result)

            return f"🧮 {expression} = {formatted_result}"

        except ZeroDivisionError:
            return "エラー: ゼロで割ることはできません"
        except ValueError as e:
            return f"エラー: 数値エラー - {str(e)}"
        except SyntaxError:
            return "エラー: 計算式の構文が正しくありません"
        except Exception as e:
            logger.error(f"Calculation error: {e}")
            return f"エラー: 計算に失敗しました - {str(e)}"

    def _is_safe_expression(self, expression: str) -> bool:
        """式が安全かどうかをチェック"""
        # 危険なキーワードをチェック
        dangerous_keywords = [
            'import', 'exec', 'eval', '__', 'open', 'file',
            'input', 'raw_input', 'compile', 'globals', 'locals',
            'vars', 'dir', 'getattr', 'setattr', 'delattr'
        ]

        expression_lower = expression.lower()
        for keyword in dangerous_keywords:
            if keyword in expression_lower:
                return False

        # 許可された文字のみかチェック
        allowed_chars = set('0123456789+-*/().abcdefghijklmnopqrstuvwxyz_,= ')
        return all(c in allowed_chars for c in expression_lower)

    def _preprocess_expression(self, expression: str) -> str:
        """式の前処理"""
        # ^ を ** に変換（べき乗）
        expression = expression.replace('^', '**')

        # 三角関数の度数変換（sin(30) -> sin(radians(30))）
        trig_functions = ['sin', 'cos', 'tan', 'asin', 'acos', 'atan']
        for func in trig_functions:
            # 度数での計算を想定してradiansで包む
            pattern = f'{func}\\((\\d+(?:\\.\\d+)?)\\)'
            if re.search(pattern, expression):
                if func in ['sin', 'cos', 'tan']:
                    expression = re.sub(
                        pattern,
                        f'{func}(radians(\\1))',
                        expression
                    )

        return expression

    async def _handle_unit_conversion(self, conversion: str) -> str:
        """単位変換を処理"""
        try:
            # 単位変換パターンの解析
            # 例: "100 cm to m", "32 F to C", "5 ft to cm"
            match = re.match(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)\s+to\s+([a-zA-Z]+)', conversion.lower())

            if not match:
                return "エラー: 単位変換の形式が正しくありません（例: 100 cm to m）"

            value = float(match.group(1))
            from_unit = match.group(2)
            to_unit = match.group(3)

            # 温度変換の特別処理
            if from_unit in ['f', 'c', 'k'] or to_unit in ['f', 'c', 'k']:
                return await self._convert_temperature(value, from_unit, to_unit)

            # 一般的な単位変換
            return await self._convert_general_units(value, from_unit, to_unit)

        except Exception as e:
            logger.error(f"Unit conversion error: {e}")
            return f"単位変換エラー: {str(e)}"

    async def _convert_temperature(self, value: float, from_unit: str, to_unit: str) -> str:
        """温度変換"""
        # 摂氏に統一してから変換
        if from_unit.lower() == 'f':
            celsius = (value - 32) * 5/9
        elif from_unit.lower() == 'k':
            celsius = value - 273.15
        else:  # celsius
            celsius = value

        # 目的の単位に変換
        if to_unit.lower() == 'f':
            result = celsius * 9/5 + 32
            unit_name = "華氏"
        elif to_unit.lower() == 'k':
            result = celsius + 273.15
            unit_name = "ケルビン"
        else:  # celsius
            result = celsius
            unit_name = "摂氏"

        return f"🌡️ {value}°{from_unit.upper()} = {result:.2f}°{to_unit.upper()} ({unit_name})"

    async def _convert_general_units(self, value: float, from_unit: str, to_unit: str) -> str:
        """一般的な単位変換"""
        # 単位の種類を特定
        unit_type = None
        from_factor = None
        to_factor = None

        for category, units in self.unit_conversions.items():
            if category == 'temperature':
                continue

            if from_unit in units and to_unit in units:
                unit_type = category
                from_factor = units[from_unit]
                to_factor = units[to_unit]
                break

        if unit_type is None:
            return f"エラー: {from_unit} から {to_unit} への変換はサポートされていません"

        # 変換実行
        # 基準単位（メートル、キログラム等）を経由して変換
        base_value = value * from_factor
        result = base_value / to_factor

        # 結果の整形
        if result == int(result):
            result_str = str(int(result))
        else:
            result_str = f"{result:.6f}".rstrip('0').rstrip('.')

        # カテゴリ別の絵文字
        category_icons = {
            'length': '📏',
            'weight': '⚖️',
            'time': '⏰'
        }

        icon = category_icons.get(unit_type, '🔄')

        return f"{icon} {value} {from_unit} = {result_str} {to_unit}"

    async def calculate_statistics(self, numbers: List[float]) -> Dict[str, float]:
        """統計値を計算"""
        if not numbers:
            return {}

        sorted_numbers = sorted(numbers)
        n = len(numbers)

        stats = {
            'count': n,
            'sum': sum(numbers),
            'mean': sum(numbers) / n,
            'min': min(numbers),
            'max': max(numbers),
            'range': max(numbers) - min(numbers)
        }

        # 中央値
        if n % 2 == 0:
            stats['median'] = (sorted_numbers[n//2 - 1] + sorted_numbers[n//2]) / 2
        else:
            stats['median'] = sorted_numbers[n//2]

        # 分散と標準偏差
        mean = stats['mean']
        variance = sum((x - mean) ** 2 for x in numbers) / n
        stats['variance'] = variance
        stats['std_dev'] = math.sqrt(variance)

        return stats