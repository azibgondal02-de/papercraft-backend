from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, constr, Field

# ============= Board Models =============

class BoardModel(BaseModel):
    board_id: int
    board_name: str


class BoardsResponse(BaseModel):
    message: str
    boards: List[BoardModel]


# ============= Class Models =============

class ClassModel(BaseModel):
    class_id: int
    board_id: int
    class_name: str


class ClassesResponse(BaseModel):
    message: str
    classes: List[ClassModel]


# ============= Subject Models =============

class SubjectModel(BaseModel):
    subject_id: int
    class_id: int
    subject_name: str
    old_subject: int


class SubjectsResponse(BaseModel):
    message: str
    subjects: List[SubjectModel]


# ============= Chapter Models =============

class ChapterModel(BaseModel):
    chapter_id: Optional[int] = None
    chapter_code: str
    chapter_name_en: Optional[str] = None
    chapter_name_urdu: Optional[str] = None
    topics: List[str]

class ChaptersResponse(BaseModel):
    message: str
    data: list[ChapterModel]
    



# ============= Topic Models =============

class TopicModel(BaseModel):
    id: str = Field(alias="topic_id")
    name_en: Optional[str] = Field(alias="topic_name_en")
    name_ur: Optional[str] = Field(alias="topic_name_urdu", default=None)

    class Config:
        populate_by_name = True


class ChapterWithTopicsModel(BaseModel):
    chapter_id: Optional[int] = None
    chapter_code: str
    chapter_name_en: Optional[str] = None
    chapter_name_ur: Optional[str] = None
    topics: List[TopicModel]




class TopicsResponse(BaseModel):
    message: str
    data: List[ChapterWithTopicsModel]


# class ChaptersResponse(BaseModel):
#     chapter_code: str
#     chapter_id: Optional[str] = None
#     chapter_name_en: Optional[str] = None
#     chapter_name_ur: Optional[str] = None



# ============= Question Models =============

class QuestionOptionModel(BaseModel):
    option_id: int
    question_id: int
    option_en: Optional[str] = None
    option_ur: Optional[str] = None
    is_correct: bool = False


class QuestionModel(BaseModel):
    id: int
    chapter_id: int
    topic_id: str
    type_id: int
    statement_en: Optional[str] = None
    statement_ur: Optional[str] = None
    answer_en: Optional[str] = None
    answer_ur: Optional[str] = None
    description_en: Optional[str] = None
    description_ur: Optional[str] = None
    exercise: Optional[str] = None
    exercise_question: int = 0
    past_paper_questions: int = False
    paragraph_questions: Optional[str] = None
    afaq: Optional[int] = None
    status: bool = True
    status_pef: bool = True
    is_table: bool = False
    is_creative: int = 0
    created_at: Optional[datetime] = None
    options: List[QuestionOptionModel] = []


class GetQuestionsRequest(BaseModel):
    class_id: int
    chapter_ids: Optional[str] = None
    topics: Optional[str] = None        # Case 2: comma-separated topic IDs
    exercise_ids: Optional[str] = None  # Case 1: comma-separated topic_name_en values
    exercise_question: Optional[str] = None
    type_id: Optional[int] = None


class QuestionsResponse(BaseModel):
    message: str
    total_count: Optional[int] = None
    questions: List[QuestionModel]
    

class PaperConfigResponse(BaseModel):
    subject_id: int
    sections: list[dict[str, Any]] = Field(default_factory=list)
    total_dataset_questions: int | None = None


from typing import List, Optional
from pydantic import BaseModel, Field


# ============== Request Models ==============
class QuestionSelection(BaseModel):
    """Single question type or part selection"""
    type_id: int
    type_name: str
    is_random: bool = Field(..., description="True = system picks, False = user selected")
    count: int = Field(..., ge=1)
    marks_per_question: float = Field(..., ge=0)
    selected_question_ids: List[int] = Field(default_factory=list, description="Empty if is_random=True")
    chapter_ids: Optional[str] = None
    topics: List[str] = Field(default_factory=list, description="Filter by these topics")
    has_choice: bool = Field(default=False, description="Show choice (attempt X of Y)")
    choice_count: Optional[int] = Field(None, description="If has_choice=True, how many to show")
    
    # For long questions with parts
    part_id: Optional[str] = Field(None, description="Part identifier like A, B, C (only for long questions)")
    group_name: Optional[str] = Field(None, description="Group name like 'Long Question 1' (only for long questions)")


class Section(BaseModel):
    """Universal section model"""
    section_key: str = Field(..., description="objective, subjective_with_board_pattern, etc.")
    section_title: str = Field(..., description="Section title to display")
    order: int = Field(..., ge=1)
    questions: List[QuestionSelection] = Field(..., description="All questions/parts in this section")


class GenerateQuestionsRequest(BaseModel):
    """Main API request"""
    subject_id: int
    sections: List[Section]
    total_marks: Optional[float] = None


# ============== Response Models ==============
class QuestionOption(BaseModel):
    """Question option"""
    option_id: int
    option_en: Optional[str] = None
    option_ur: Optional[str] = None
    is_correct: bool


class QuestionDetail(BaseModel):
    """Single question detail"""
    question_id: int
    statement_en: Optional[str] = None
    statement_ur: Optional[str] = None
    answer_en: Optional[str] = None
    answer_ur: Optional[str] = None
    description_en: Optional[str] = None
    description_ur: Optional[str] = None
    marks: float
    options: List[QuestionOption] = Field(default_factory=list)


class QuestionGroup(BaseModel):
    """Group of questions by type"""
    type_id: int
    type_name: str
    count: int
    marks_per_question: float
    questions_total_marks: float
    questions: List[QuestionDetail]
    has_choice: bool = False
    choice_count: Optional[int] = None
    part_id: Optional[str] = None
    group_name: Optional[str] = None


class SectionResponse(BaseModel):
    """Section with questions"""
    section_key: str
    section_title: str
    order: int
    total_marks: float
    question_groups: List[QuestionGroup]


class GenerateQuestionsResponse(BaseModel):
    """API Response"""
    subject_id: int
    sections: List[SectionResponse]
    total_marks: float
    total_questions: int
    message: str = "Questions generated successfully"