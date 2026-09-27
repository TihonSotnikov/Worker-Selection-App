"""
Демо-вакансии. Компании и адреса вымышлены.
"""

from app.core.enums import Amenity, CertKind, Profession, ShiftSchedule, TeamFormat, Zone
from app.core.schemas import CertRequirement, SkillRequirement, VacancyData

DEMO_VACANCIES: list[VacancyData] = [
    VacancyData(
        title="Оператор фрезерного ЧПУ",
        company="ТехноПром",
        profession=Profession.CNC,
        zone=Zone.LEFT_BANK,
        shift=ShiftSchedule.ROTATING,
        salary=115_000,
        requirements=[
            SkillRequirement(skill="cnc_milling", min_years=3),
            SkillRequirement(skill="fanuc", min_years=2),
        ],
        certificates=[CertRequirement(kind=CertKind.GRADE, min_level=4)],
        amenities=[Amenity.CANTEEN, Amenity.SHOWER, Amenity.SHUTTLE],
        team_format=TeamFormat.MIXED,
        description="Серийное производство корпусных деталей для энергетики, трёхосевые обрабатывающие центры.",
    ),
    VacancyData(
        title="Токарь-оператор ЧПУ, дневные смены",
        company="СеверМаш",
        profession=Profession.CNC,
        zone=Zone.NORTH,
        shift=ShiftSchedule.DAY,
        salary=95_000,
        requirements=[
            SkillRequirement(skill="cnc_turning", min_years=2),
            SkillRequirement(skill="blueprints", min_years=1),
        ],
        certificates=[CertRequirement(kind=CertKind.GRADE, min_level=3)],
        amenities=[Amenity.CANTEEN],
        team_format=TeamFormat.TEAM,
        description="Валы и втулки для насосного оборудования, мелкие серии.",
    ),
    VacancyData(
        title="Сварщик TIG, нержавейка, ночные смены",
        company="Сталь-Конструкция",
        profession=Profession.WELDER,
        zone=Zone.SOUTH,
        shift=ShiftSchedule.NIGHT,
        salary=125_000,
        requirements=[
            SkillRequirement(skill="tig", min_years=3),
            SkillRequirement(skill="stainless", min_years=1),
        ],
        certificates=[CertRequirement(kind=CertKind.NAKS)],
        amenities=[Amenity.CANTEEN, Amenity.SHOWER, Amenity.DORMITORY],
        team_format=TeamFormat.MIXED,
        description="Трубопроводы и ёмкости из нержавеющей стали для пищевой промышленности.",
    ),
    VacancyData(
        title="Сварщик-полуавтоматчик",
        company="ТехноПром",
        profession=Profession.WELDER,
        zone=Zone.LEFT_BANK,
        shift=ShiftSchedule.DAY,
        salary=85_000,
        requirements=[
            SkillRequirement(skill="mig_mag", min_years=1),
            SkillRequirement(skill="mma", min_years=1),
        ],
        certificates=[CertRequirement(kind=CertKind.GRADE, min_level=3)],
        amenities=[Amenity.CANTEEN, Amenity.SHOWER, Amenity.SHUTTLE],
        team_format=TeamFormat.TEAM,
        description="Сварка рам и металлоконструкций в бригаде, дневной график.",
    ),
    VacancyData(
        title="Электромеханик по ремонту оборудования",
        company="ПромАвтоматика",
        profession=Profession.ELECTRO,
        zone=Zone.CENTER,
        shift=ShiftSchedule.ROTATING,
        salary=105_000,
        requirements=[
            SkillRequirement(skill="equipment_repair", min_years=3),
            SkillRequirement(skill="hydraulics", min_years=1),
        ],
        certificates=[CertRequirement(kind=CertKind.ELSAFETY, min_level=3)],
        amenities=[Amenity.CANTEEN, Amenity.SHOWER],
        team_format=TeamFormat.TEAM,
        description="Обслуживание прессов и станочного парка, аварийные вызовы в смену.",
    ),
    VacancyData(
        title="Электромонтёр-наладчик, дневные смены",
        company="СеверМаш",
        profession=Profession.ELECTRO,
        zone=Zone.NORTH,
        shift=ShiftSchedule.DAY,
        salary=90_000,
        requirements=[
            SkillRequirement(skill="electrical_install", min_years=2),
            SkillRequirement(skill="drives", min_years=1),
        ],
        certificates=[CertRequirement(kind=CertKind.ELSAFETY, min_level=3)],
        amenities=[Amenity.CANTEEN, Amenity.SHUTTLE],
        team_format=TeamFormat.MIXED,
        description="Монтаж и наладка шкафов управления, пусконаладка новых линий.",
    ),
]
