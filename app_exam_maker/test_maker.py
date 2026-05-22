from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer
from lib_exam_maker.models.test_maker import (
    BoardsResponse,
    ChaptersResponse,
    ClassesResponse,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    SubjectsResponse,
    TopicsResponse,
    QuestionsResponse,
    GetQuestionsRequest,
    PaperConfigResponse
)
from lib_exam_maker.test_maker import (
    generate_questions,
    get_boards,
    get_chapters_against_subject,
    get_classes_against_board,
    get_subjects_against_class_board,
    get_topics_against_subject,
    get_questions,
    get_paper_config
)
from lib_identity.identity import require_auth
from web import get_context_with_user_info

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


@router.get("/get_boards", dependencies=[Depends(bearer_scheme)], tags=["Test Maker"])
@require_auth
def fetch_boards(request: Request) -> BoardsResponse:
    """
    Fetch all available boards from the Boards Table
    """
    context, user_code, user_type = get_context_with_user_info(request)
    boards = get_boards(conn=context.conn)
    
    return BoardsResponse(
        message="Boards fetched successfully",
        boards=boards
    )


@router.get("/get_classes_against_board/{board_id}", dependencies=[Depends(bearer_scheme)], tags=["Test Maker"])
@require_auth
def fetch_classes_by_board(board_id: int, request: Request) -> ClassesResponse:
    """
    Fetch all classes associated with a specific board
    """
    context, user_code, user_type = get_context_with_user_info(request)
    classes = get_classes_against_board(conn=context.conn, board_id=board_id)
    
    return ClassesResponse(
        message="Classes fetched successfully",
        classes=classes
    )


@router.get("/get_subjects_against_class_board/{class_id}", dependencies=[Depends(bearer_scheme)], tags=["Test Maker"])
@require_auth
def fetch_subjects_by_class(class_id: int, request: Request) -> SubjectsResponse:
    """
    Fetch all subjects for a specific class
    """
    context, user_code, user_type = get_context_with_user_info(request)
    subjects = get_subjects_against_class_board(conn=context.conn, class_id=class_id)
    
    return SubjectsResponse(
        message="Subjects fetched successfully",
        subjects=subjects
    )


@router.get("/get_topics_against_subject/{subject_id}", dependencies=[Depends(bearer_scheme)], tags=["Test Maker"])
@require_auth
def fetch_topics_by_subject(subject_id: int, request: Request) -> TopicsResponse:
    """
    Fetch all chapters and topics for a specific subject
    """
    context, user_code, user_type = get_context_with_user_info(request)
    topics = get_topics_against_subject(conn=context.conn, subject_id=subject_id)
    
    return TopicsResponse(
        message="Topics fetched successfully",
        data=topics
    )

@router.get("/get_chapters_against_subject/{subject_id}", dependencies=[Depends(bearer_scheme)], tags=["Test Maker"])
@require_auth
def fetch_chapters_by_subject(subject_id: int, request: Request) -> ChaptersResponse:
    """
    Fetch all chapters for a specific subject
    """
    context, user_code, user_type = get_context_with_user_info(request)
    return get_chapters_against_subject(conn=context.conn, subject_id=subject_id)


@router.post("/get_questions", dependencies=[Depends(bearer_scheme)], tags=["Test Maker"])
@require_auth
def fetch_questions(payload: GetQuestionsRequest, request: Request) -> QuestionsResponse:
    """
    Fetch questions based on filters like class_id, chapter_ids, topics, exercise types, etc.
    """
    context, user_code, user_type = get_context_with_user_info(request)
    questions = get_questions(conn=context.conn, payload=payload)
    
    return QuestionsResponse(
        message="Questions fetched successfully",
        total_count=len(questions),
        questions=questions
    )


@router.get(
    "/paper-config/{subject_id}",
    dependencies=[Depends(bearer_scheme)],
    tags=["Test Maker"],
)
@require_auth
def get(subject_id: int, request: Request) -> PaperConfigResponse:
    context, user_code, user_type = get_context_with_user_info(request)
    return get_paper_config(conn=context.conn, subject_id=subject_id)


@router.post("/generate-questions", dependencies=[Depends(bearer_scheme)], tags=["Questions"])
@require_auth
def generate_paper_questions(payload: GenerateQuestionsRequest, request: Request) -> GenerateQuestionsResponse:
    """
    Generate questions for paper based on user selection or random selection
    """
    context, user_code, user_type = get_context_with_user_info(request)
    
    response = generate_questions(
        conn=context.conn,
        user_code=user_code,
        payload=payload
    )
    
    return response