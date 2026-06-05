from pydantic import BaseModel, Field, field_validator


class SparkTargetCreate(BaseModel):
    nickname: str
    remark: str | None = None
    receiver_id: str | None = None
    custom_template: str | None = None
    enabled: bool = True


class SparkTargetUpdate(BaseModel):
    nickname: str | None = None
    remark: str | None = None
    receiver_id: str | None = None
    custom_template: str | None = None
    enabled: bool | None = None


class SparkTargetOut(BaseModel):
    id: int
    nickname: str
    remark: str | None = None
    receiver_id: str | None = None
    custom_template: str | None = None
    enabled: bool
    last_status: str | None = None
    last_run_at: str | None = None
    last_error: str | None = None


class SparkTargetListResponse(BaseModel):
    items: list[SparkTargetOut]
    total: int


class BatchIdsRequest(BaseModel):
    ids: list[int]


class SparkSettingsOut(BaseModel):
    enabled: bool
    execute_time: str
    default_template: str | None = None
    random_template_enabled: bool
    daily_limit: int
    skip_today: bool


class SparkSettingsUpdate(BaseModel):
    enabled: bool | None = None
    execute_time: str | None = None
    default_template: str | None = None
    random_template_enabled: bool | None = None
    daily_limit: int | None = None

    @field_validator("execute_time")
    @classmethod
    def validate_execute_time(cls, v: str | None) -> str | None:
        if v is None:
            return v
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("execute_time 格式应为 HH:mm")
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("execute_time 无效")
        return v

    @field_validator("daily_limit")
    @classmethod
    def validate_daily_limit(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 100):
            raise ValueError("daily_limit 范围为 1-100")
        return v


class RunNowResponse(BaseModel):
    job_status: str
    message: str


class SkipTodayResponse(BaseModel):
    skip_today: bool


class TodayStatusResponse(BaseModel):
    execute_date: str
    target_count: int
    success_count: int
    failed_count: int
    unsupported_count: int
    skipped_count: int
    job_status: str
    last_execute_at: str | None = None


class SparkRecordOut(BaseModel):
    id: int
    execute_date: str
    execute_time: str
    target_nickname: str | None = None
    message: str | None = None
    channel: str
    status: str
    error_message: str | None = None


class SparkRecordListResponse(BaseModel):
    items: list[SparkRecordOut]
    total: int
