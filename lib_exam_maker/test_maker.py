import json
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any, Optional, Set
from lib_exam_maker.models.test_maker import (
    BoardModel,
    ChapterModel,
    ChaptersResponse,
    ClassModel,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    QuestionDetail,
    QuestionGroup,
    QuestionOption,
    QuestionSelection,
    QuestionsResponse,
    SectionResponse,
    SubjectModel,
    ChapterWithTopicsModel,
    TopicModel,
    QuestionModel,
    QuestionOptionModel,
    GetQuestionsRequest,
    PaperConfigResponse
)
from lib_utils.sql import sql


def get_boards(conn) -> List[BoardModel]:
    """
    Fetch all boards from the boards_bank table
    """
    try:
        boards_data = sql(
            conn,
            """
            SELECT board_id, board_name
            FROM boards_bank
            ORDER BY board_name
            """
        ).dicts()
        
        if not boards_data:
            return []
        
        return [BoardModel(**board) for board in boards_data]
    
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching boards"
        )


def get_classes_against_board(conn, board_id: int) -> List[ClassModel]:
    """
    Fetch all classes for a specific board
    """
    try:
        # First verify board exists
        board = sql(
            conn,
            "SELECT board_id FROM boards_bank WHERE board_id = :board_id",
            {"board_id": board_id}
        ).dict()
        
        if not board:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Board not found"
            )
        
        classes_data = sql(
            conn,
            """
            SELECT class_id, board_id, class_name
            FROM classes_bank
            WHERE board_id = :board_id
            ORDER BY class_id
            """,
            {"board_id": board_id}
        ).dicts()
        
        if not classes_data:
            return []
        
        return [ClassModel(**cls) for cls in classes_data]
    
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching classes"
        )


def get_subjects_against_class_board(conn, class_id: int) -> List[SubjectModel]:
    """
    Fetch all subjects for a specific class
    """
    try:
        # First verify class exists
        cls = sql(
            conn,
            "SELECT class_id FROM classes_bank WHERE class_id = :class_id",
            {"class_id": class_id}
        ).dict()
        
        if not cls:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Class not found"
            )
        
        subjects_data = sql(
            conn,
            """
            SELECT subject_id, class_id, subject_name, old_subject
            FROM subjects_bank
            WHERE class_id = :class_id
            ORDER BY subject_name
            """,
            {"class_id": class_id}
        ).dicts()
        
        if not subjects_data:
            return []
        
        return [SubjectModel(**subject) for subject in subjects_data]
    
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching subjects"
        )


def get_topics_against_subject(conn, subject_id: int) -> List[ChapterWithTopicsModel]:
    """
    Fetch all chapters and their topics for a specific subject
    Returns a structured response with chapters and nested topics
    """
    try:
        # First verify subject exists
        subject = sql(
            conn,
            "SELECT subject_id FROM subjects_bank WHERE subject_id = :subject_id",
            {"subject_id": subject_id}
        ).dict()
        
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subject not found"
            )
        
        # Fetch chapters for the subject
        chapters_data = sql(
            conn,
            """
            SELECT chapter_code, chapter_id, subject_id, chapter_name_en, chapter_name_urdu
            FROM chapters_bank
            WHERE subject_id = :subject_id
            ORDER BY CAST(REGEXP_SUBSTR(chapter_name_en, '[0-9]+') AS UNSIGNED) ASC,
            CAST(REGEXP_SUBSTR(chapter_name_urdu, '[0-9]+') AS UNSIGNED) ASC
            """,
            {"subject_id": subject_id}
        ).dicts()
        
        if not chapters_data:
            return []
        
        # Fetch all topics for these chapters
        chapter_codes = [ch['chapter_code'] for ch in chapters_data if ch['chapter_code'] is not None]

        topics_by_chapter = {}

        if chapter_codes:
            placeholders = ','.join([f':ch_{i}' for i in range(len(chapter_codes))])
            topics_data = sql(
                conn,
                f"""
                SELECT t.topic_id, t.chapter_code, t.topic_name_en, t.topic_name_urdu, c.chapter_id
                FROM topics_bank t
                JOIN chapters_bank c ON t.chapter_code = c.chapter_code
                WHERE t.chapter_code IN ({placeholders})
                ORDER BY topic_name_en, topic_name_urdu
                """,
                {f'ch_{i}': code for i, code in enumerate(chapter_codes)}
            ).dicts()

            for topic in topics_data:
                chapter_code = topic['chapter_code']
                if chapter_code not in topics_by_chapter:
                    topics_by_chapter[chapter_code] = []
                topics_by_chapter[chapter_code].append(TopicModel(**{
                    'topic_id': str(topic['topic_id']),
                    'chapter_id': str(topic['chapter_id']),  # from JOIN
                    'topic_name_en': topic['topic_name_en'],
                    'topic_name_urdu': topic['topic_name_urdu'],
                }))
        
        # Build the response structure
        result = []
        for chapter in chapters_data:
            chapter_code = chapter['chapter_code']
            result.append(
                ChapterWithTopicsModel(
                    chapter_id=chapter.get('chapter_id', ''),
                    chapter_code = chapter.get("chapter_code"),
                    chapter_name_en=chapter['chapter_name_en'],
                    chapter_name_ur=chapter.get('chapter_name_urdu'),
                    topics=topics_by_chapter.get(chapter_code, [])
                )
            )
        
        return result
    
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        print(exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching topics"
        )

def get_chapters_against_subject(conn, subject_id: int) -> ChaptersResponse:
    """
    Fetch all chapters for a specific subject with their associated topics (optimized)
    """
    try:
        # First verify subject exists
        subject = sql(
            conn,
            "SELECT subject_id FROM subjects_bank WHERE subject_id = :subject_id",
            {"subject_id": subject_id}
        ).dict()
        
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subject not found"
            )
        
        # Fetch chapters with topics in a single query using LEFT JOIN
        results = sql(
            conn,
            """
            SELECT 
                c.chapter_code, 
                c.chapter_id, 
                c.chapter_name_en, 
                c.chapter_name_urdu,
                t.topic_id
            FROM chapters_bank c
            LEFT JOIN topics_bank t ON c.chapter_code = t.chapter_code
            WHERE c.subject_id = :subject_id
            ORDER BY 
                CAST(REGEXP_SUBSTR(c.chapter_name_en, '[0-9]+') AS UNSIGNED) ASC,
                CAST(REGEXP_SUBSTR(c.chapter_name_urdu, '[0-9]+') AS UNSIGNED) ASC,
                t.topic_name_en, 
                t.topic_name_urdu
            """,
            {"subject_id": subject_id}
        ).dicts()
        
        if not results:
            return ChaptersResponse(
                message="No chapters found for this subject",
                data=[]
            )
        
        # Group topics by chapter
        chapters_dict = {}
        for row in results:
            chapter_code = row['chapter_code']
            
            # Initialize chapter if not seen before
            if chapter_code not in chapters_dict:
                chapters_dict[chapter_code] = {
                    'chapter_id': row['chapter_id'],
                    'chapter_code': row['chapter_code'],
                    'chapter_name_en': row['chapter_name_en'],
                    'chapter_name_urdu': row['chapter_name_urdu'],
                    'topics': []
                }
            
            # Add topic_id if it exists (LEFT JOIN may have NULL topics)
            if row['topic_id'] is not None:
                chapters_dict[chapter_code]['topics'].append(str(row['topic_id']))
        
        # Convert to list of ChapterModel objects
        chapters = [ChapterModel(**chapter_data) for chapter_data in chapters_dict.values()]

        return ChaptersResponse(
            message="Chapters fetched successfully",
            data=chapters
        )
    
    except HTTPException:
        raise
# ========================
# CORE FUNCTION
# ========================

def get_questions(conn, payload: GetQuestionsRequest) -> List[QuestionModel]:
    try:
        where_conditions = []
        query_params = {}

        chapter_list = (
            [
                c.strip()
                for c in payload.chapter_ids.split(',')
                if c.strip() and c.strip().lower() != 'none'
            ]
            if payload.chapter_ids else []
        )

        topic_list = (
            [c.strip() for c in payload.topics.split(',') if c.strip().lower() != 'none']
            if payload.topics else []
        )

        isMath = True if topic_list and not topic_list[0].isdigit() else False
        # ========================
        # Case 2: topic_ids provided → search directly by topic_id
        # ========================
        if payload.topics and chapter_list and not isMath:
            topic_list = [topic.strip() for topic in payload.topics.split(',')]
            placeholders = ','.join([f':topic_{i}' for i in range(len(topic_list))])
            where_conditions.append(f"q.topic_id IN ({placeholders})")
            for i, topic_id in enumerate(topic_list):
                query_params[f'topic_{i}'] = topic_id

        # ========================
        # Case 1: no topic_ids → search by chapter_ids + exercise_ids (topic_name_en)
        # ========================
        elif payload.topics and payload.chapter_ids and isMath:
            chapter_list = [ch.strip() for ch in payload.chapter_ids.split(',')]
            topic_list = [ex.strip() for ex in payload.topics.split(',')]

            # Filter by chapter_id
            chapter_placeholders = ','.join([f':ch_{i}' for i in range(len(chapter_list))])
            where_conditions.append(f"q.chapter_id IN ({chapter_placeholders})")
            for i, ch in enumerate(chapter_list):
                query_params[f'ch_{i}'] = ch

            # Filter directly by q.exercise column (topic_id is NULL in this case)
            topic_placeholders = ','.join([f':ex_name_{i}' for i in range(len(topic_list))])
            where_conditions.append(f"q.topic_id IN ({topic_placeholders})")
            for i, ex in enumerate(topic_list):
                query_params[f'ex_name_{i}'] = ex

        else:
            topic_list = [topic.strip() for topic in payload.topics.split(',')]
            placeholders = ','.join([f':topic_{i}' for i in range(len(topic_list))])
            where_conditions.append(f"q.chapter_id IN ({placeholders})")
            for i, topic_id in enumerate(topic_list):
                query_params[f'topic_{i}'] = topic_id

        # ========================
        # Filter by exercise_question
        # ========================
        if payload.exercise_question:
            exercise_list = [int(ex.strip()) for ex in payload.exercise_question.split(',')]
            placeholders = ','.join([f':exercise_{i}' for i in range(len(exercise_list))])
            where_conditions.append(f"q.exercise_question IN ({placeholders})")
            for i, exercise_val in enumerate(exercise_list):
                query_params[f'exercise_{i}'] = exercise_val

        # ========================
        # Filter by type_id
        # ========================
        if payload.type_id:
            where_conditions.append("q.type_id = :type_id")
            query_params['type_id'] = payload.type_id

        # ========================
        # Build WHERE clause
        # ========================
        if not where_conditions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one filter must be provided"
            )

        where_clause = " AND ".join(where_conditions)

        # ========================
        # Main query
        # ========================
        questions_query = f"""
            SELECT 
                q.id,
                q.chapter_id,
                q.medium,
                q.topic_id,
                q.type_id,
                q.statement_en,
                q.statement_ur,
                q.answer_en,
                q.answer_ur,
                q.description_en,
                q.description_ur,
                q.exercise,
                q.exercise_question,
                q.past_paper_questions,
                q.paragraph_questions,
                q.afaq,
                q.status,
                q.status_pef,
                q.is_table,
                q.is_creative,
                q.created_at
            FROM questions_bank q
            WHERE {where_clause}
            ORDER BY q.id
        """

        questions_data = sql(conn, questions_query, query_params).dicts()

        if not questions_data:
            return []

        # ========================
        # Fetch options in one query
        # ========================
        question_ids = [q['id'] for q in questions_data]
        placeholders = ','.join([f':qid_{i}' for i in range(len(question_ids))])
        options_query = f"""
            SELECT 
                option_id,
                question_id,
                option_en,
                option_ur,
                is_correct
            FROM question_options_bank
            WHERE question_id IN ({placeholders})
            ORDER BY question_id, option_id
        """
        options_params = {f'qid_{i}': qid for i, qid in enumerate(question_ids)}
        options_data = sql(conn, options_query, options_params).dicts()

        # ========================
        # Group options by question_id
        # ========================
        options_by_question = {}
        for option in options_data:
            q_id = option['question_id']
            if q_id not in options_by_question:
                options_by_question[q_id] = []
            options_by_question[q_id].append(QuestionOptionModel(**option))

        # ========================
        # Build final question models
        # ========================
        questions = []
        for q_data in questions_data:
            q_id = q_data['id']
            q_dict = dict(q_data)
            q_dict['options'] = options_by_question.get(q_id, [])
            questions.append(QuestionModel(**q_dict))

        return questions

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter format: {str(exc)}"
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching questions"
        )

def get_paper_config(conn, subject_id: int) -> PaperConfigResponse:
    try:
        config = sql(
            conn,
            """
            SELECT subject_id, sections, total_dataset_questions
            FROM paper_configs_bank
            WHERE subject_id = :subject_id
            LIMIT 1
            """,
            {"subject_id": subject_id},
        ).dict()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper config not found for this subject",
        )

    sections = config.get("sections")
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except (TypeError, ValueError):
            sections = []
    elif sections is None:
        sections = []

    return PaperConfigResponse(
        subject_id=config["subject_id"],
        sections=sections,
        total_dataset_questions=config.get("total_dataset_questions"),
    )


def generate_questions(
    conn, 
    user_code: str, 
    payload: GenerateQuestionsRequest
) -> GenerateQuestionsResponse:
    """
    Main function to generate questions based on payload
    """
    try:
        sections_response = []
        used_question_ids: Set[int] = set()  # Track used questions to prevent duplicates
        total_questions = 0
        
        for section in payload.sections:
            section_total_marks = 0
            question_groups = []
            
            for question_sel in section.questions:
                # Get questions based on selection
                questions = _get_questions_for_selection(
                    conn=conn,
                    selection=question_sel,
                    subject_id=payload.subject_id,
                    used_question_ids=used_question_ids
                )
                
                # Build question group
                group = QuestionGroup(
                    type_id=question_sel.type_id,
                    type_name=question_sel.type_name,
                    marks_per_question=question_sel.marks_per_question,
                    questions_total_marks=(question_sel.count - question_sel.choice_count) * question_sel.marks_per_question,
                    count=question_sel.count,
                    questions=questions,
                    has_choice=question_sel.has_choice,
                    choice_count=question_sel.choice_count,
                    part_id=question_sel.part_id if question_sel.part_id else None,
                    group_name=question_sel.group_name if question_sel.group_name else None
                )
                
                question_groups.append(group)
                if question_sel.has_choice:
                    section_total_marks += question_sel.choice_count * question_sel.marks_per_question
                else:
                    section_total_marks += len(questions) * question_sel.marks_per_question
                total_questions += len(questions)
            
            sections_response.append(
                SectionResponse(
                    section_key=section.section_key,
                    section_title=section.section_title,
                    order=section.order,
                    total_marks=section_total_marks,
                    question_groups=question_groups
                )
            )
        
        return GenerateQuestionsResponse(
            subject_id=payload.subject_id,
            sections=sections_response,
            total_marks=sum(s.total_marks for s in sections_response),
            total_questions=total_questions
        )
        
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while generating questions"
        )


def _get_questions_for_selection(
    conn,
    selection: QuestionSelection,
    subject_id: int,
    used_question_ids: Set[int]
) -> List[QuestionDetail]:
    """
    Get questions based on selection criteria (random or user-selected)
    """
    if not selection.is_random:
        # User selected specific questions
        return _get_selected_questions(
            conn=conn,
            question_ids=selection.selected_question_ids,
            marks=selection.marks_per_question,
            used_question_ids=used_question_ids
        )
    else:
        # System random selection
        return _get_random_questions(
            conn=conn,
            subject_id=subject_id,
            type_id=selection.type_id,
            count=selection.count,
            topics=selection.topics,
            chapter_ids=selection.chapter_ids,
            marks=selection.marks_per_question,
            used_question_ids=used_question_ids
        )


def _get_selected_questions(
    conn,
    question_ids: List[int],
    marks: float,
    used_question_ids: Set[int]
) -> List[QuestionDetail]:
    """
    Get specific questions selected by user
    """
    if not question_ids:
        return []
    
    # Check for duplicates with already used questions
    duplicate_ids = set(question_ids) & used_question_ids
    if duplicate_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Questions already used in paper: {list(duplicate_ids)}"
        )
    
    try:
        # Get questions
        questions = sql(
            conn,
            """
            SELECT 
                id as question_id,
                topic_id,
                statement_en,
                statement_ur,
                answer_en,
                answer_ur,
                description_en,
                description_ur
            FROM questions_bank
            WHERE id IN :question_ids
                AND status = 1
            """,
            {"question_ids": tuple(question_ids)}
        ).dicts()
        
        if not questions:
            return []
        
        # Get options for these questions
        options_data = sql(
            conn,
            """
            SELECT 
                option_id,
                question_id,
                option_en,
                option_ur,
                is_correct
            FROM question_options_bank
            WHERE question_id IN :question_ids
            ORDER BY option_id
            """,
            {"question_ids": tuple(question_ids)}
        ).dicts()
        
        # Group options by question_id
        options_by_question = {}
        for opt in options_data:
            qid = opt['question_id']
            if qid not in options_by_question:
                options_by_question[qid] = []
            options_by_question[qid].append(
                QuestionOption(
                    option_id=opt['option_id'],
                    option_en=opt['option_en'],
                    option_ur=opt['option_ur'],
                    is_correct=bool(opt['is_correct'])
                )
            )
        
        # Build response
        result = []
        for q in questions:
            qid = q['question_id']
            used_question_ids.add(qid)
            
            result.append(
                QuestionDetail(
                    question_id=qid,
                    statement_en=q['statement_en'],
                    statement_ur=q['statement_ur'],
                    answer_en=q['answer_en'],
                    answer_ur=q['answer_ur'],
                    description_en=q['description_en'],
                    description_ur=q['description_ur'],
                    marks=marks,
                    options=options_by_question.get(qid, [])
                )
            )
        
        return result
        
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while fetching selected questions"
        )


def _get_random_questions(
    conn,
    subject_id: int,
    type_id: int,
    count: int,
    topics: List[str],
    marks: float,
    used_question_ids: Set[int],
    chapter_ids: Optional[str] = None
) -> List[QuestionDetail]:
    print(topics)
    print(chapter_ids)
    print("*" * 50)
    try:
        where_conditions = []
        query_params = {}

        topic_list = [str(t).strip() for t in (topics or []) if str(t).strip()]
        chapter_list = [c.strip() for c in (chapter_ids or '').split(',') if c.strip()]

        isMath = bool(topic_list and not topic_list[0].isdigit())

        if topic_list and chapter_list and not isMath:
            # Numeric topic IDs → filter by topic_id
            placeholders = ','.join([f':topic_{i}' for i in range(len(topic_list))])
            where_conditions.append(f"topic_id IN ({placeholders})")
            for i, t in enumerate(topic_list):
                query_params[f'topic_{i}'] = t

        elif topic_list and chapter_list and isMath:
            # String exercise names → filter by chapter_id AND topic_id
            placeholders = ','.join([f':ch_{i}' for i in range(len(chapter_list))])
            where_conditions.append(f"chapter_id IN ({placeholders})")
            for i, c in enumerate(chapter_list):
                query_params[f'ch_{i}'] = c
            placeholders = ','.join([f':topic_{i}' for i in range(len(topic_list))])
            where_conditions.append(f"topic_id IN ({placeholders})")
            for i, t in enumerate(topic_list):
                query_params[f'topic_{i}'] = t

        else :
            # No topics, just chapters
            placeholders = ','.join([f':topic_{i}' for i in range(len(topic_list))])
            where_conditions.append(f"chapter_id IN ({placeholders})")
            for i, topic_id in enumerate(topic_list):
                query_params[f'topic_{i}'] = topic_id

        if used_question_ids:
            placeholders = ','.join([f':used_{i}' for i in range(len(used_question_ids))])
            where_conditions.append(f"id NOT IN ({placeholders})")
            for i, uid in enumerate(used_question_ids):
                query_params[f'used_{i}'] = uid

        where_extra = ("AND " + " AND ".join(where_conditions)) if where_conditions else ""


        questions = sql(
            conn,
            f"""
            SELECT id as question_id, statement_en, statement_ur,
                   answer_en, answer_ur, description_en, description_ur
            FROM questions_bank
            WHERE type_id = :type_id AND status = 1
                {where_extra}
            ORDER BY RAND()
            LIMIT :count
            """,
            {"type_id": type_id, "count": count, **query_params}
        ).dicts()

        if not questions:
            return []

        questions = questions[:min(count, len(questions))]
        question_ids = [q['question_id'] for q in questions]

        if not question_ids:
            return []

        placeholders = ','.join([f':qid_{i}' for i in range(len(question_ids))])
        options_data = sql(
            conn,
            f"""
            SELECT option_id, question_id, option_en, option_ur, is_correct
            FROM question_options_bank
            WHERE question_id IN ({placeholders})
            ORDER BY option_id
            """,
            {f'qid_{i}': qid for i, qid in enumerate(question_ids)}
        ).dicts()

        options_by_question = {}
        for opt in options_data:
            qid = opt['question_id']
            if qid not in options_by_question:
                options_by_question[qid] = []
            options_by_question[qid].append(
                QuestionOption(
                    option_id=opt['option_id'],
                    option_en=opt['option_en'],
                    option_ur=opt['option_ur'],
                    is_correct=bool(opt['is_correct'])
                )
            )

        result = []
        for q in questions:
            qid = q['question_id']
            used_question_ids.add(qid)
            result.append(
                QuestionDetail(
                    question_id=qid,
                    statement_en=q['statement_en'],
                    statement_ur=q['statement_ur'],
                    answer_en=q['answer_en'],
                    answer_ur=q['answer_ur'],
                    description_en=q['description_en'],
                    description_ur=q['description_ur'],
                    marks=marks,
                    options=options_by_question.get(qid, [])
                )
            )

        return result

    except SQLAlchemyError as exc:
        # print(exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while fetching random questions"
        )