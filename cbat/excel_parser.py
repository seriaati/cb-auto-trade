import datetime

import pandas as pd

from .utils import convert_effective_date


class ConvertibleBond:
    def __init__(
        self,
        *,
        stock_id: str,
        stock_name: str,
        effective_date: datetime.date | None,
        case_category: str,
    ):
        self.stock_id = stock_id
        self.stock_name = stock_name
        self.effective_date = effective_date
        self.case_category = case_category

    def __str__(self) -> str:
        return f"[{self.stock_id}] {self.stock_name}: 生效日期: {self.effective_date or '無'}, 案件類別: {self.case_category}"

    @classmethod
    def parse(cls, data: dict[str, str]) -> "ConvertibleBond":
        return cls(
            stock_id=data["stock_id"],
            stock_name=data["stock_name"],
            effective_date=datetime.datetime.strptime(
                data["effective_date"], "%Y-%m-%d"
            ),
            case_category=data["case_category"],
        )

    @property
    def yahoo_url(self) -> str:
        return f"https://tw.stock.yahoo.com/q/ta?s={self.stock_id}"

    def dump_json(self) -> dict[str, str | None]:
        return {
            "stock_id": self.stock_id,
            "stock_name": self.stock_name,
            "effective_date": self.effective_date.strftime("%Y-%m-%d")
            if self.effective_date
            else None,
            "case_category": self.case_category,
        }


def get_cbs(df: pd.DataFrame) -> list[ConvertibleBond]:
    result: list[ConvertibleBond] = []
    df = df[df["案件類別"].isin(["轉換公司債(無擔保)", "轉換公司債(有擔保)"])]
    for row in df.iterrows():
        stock_id = row[1]["證券代號"]
        stock_name = row[1]["公司名稱"]
        effective_date = row[1]["生效日期"]
        case_category = row[1]["案件類別"]

        if pd.isnull(effective_date):
            effective_date = None
        else:
            effective_date = convert_effective_date(str(int(effective_date)))

        result.append(
            ConvertibleBond(
                stock_id=str(stock_id),
                stock_name=stock_name,
                effective_date=effective_date,
                case_category=case_category,
            )
        )
    return result
