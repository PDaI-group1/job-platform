INSERT INTO jobs (
    source, source_job_id, url, title, company_name, location, remote_type, employment_type,
    description, skills, language, salary_min, salary_max, salary_period, published_at, deadline_at
) VALUES
(
    'duunitori', 'seed-001', 'https://example.com/jobs/seed-001',
    'Junior Python Developer', 'Pohjoistech Oy', 'Oulu', 'hybrid', 'full_time',
    'Join our backend team building data pipelines for industrial IoT. Python, SQL and Docker experience is a plus.',
    ARRAY['python', 'sql', 'docker', 'git'], 'en', 3200, 3800, 'month',
    now() - interval '2 days', now() + interval '3 weeks'
),
(
    'oikotie', 'seed-002', 'https://example.com/jobs/seed-002',
    'Frontend Developer (React)', 'Kide Digital Oy', 'Helsinki', 'remote', 'full_time',
    'We are looking for a React developer to build modern web applications for our clients.',
    ARRAY['react', 'typescript', 'css', 'git'], 'en', 3800, 4800, 'month',
    now() - interval '5 days', now() + interval '2 weeks'
),
(
    'tyomarkkinatori', 'seed-003', 'https://example.com/jobs/seed-003',
    'Ohjelmistokehittäjä, harjoittelu', 'Revontuli Solutions Oy', 'Tampere', 'onsite', 'internship',
    'Kesäharjoittelu ohjelmistokehitystiimissä. Etsimme opiskelijaa, jolla on perustaidot Javasta tai Pythonista.',
    ARRAY['java', 'python', 'git'], 'fi', 2300, 2600, 'month',
    now() - interval '1 day', now() + interval '1 month'
),
(
    'duunitori', 'seed-004', 'https://example.com/jobs/seed-004',
    'Data Analyst', 'Saimaa Analytics Oy', 'Lappeenranta', 'hybrid', 'full_time',
    'Analyse business data and build dashboards. Strong SQL and Power BI skills required, Python is a bonus.',
    ARRAY['sql', 'power bi', 'python', 'excel'], 'en', NULL, NULL, NULL,
    now() - interval '10 days', now() + interval '5 days'
),
(
    'oikotie', 'seed-005', 'https://example.com/jobs/seed-005',
    'DevOps Engineer', 'Arctic Cloud Oy', 'Espoo', 'hybrid', 'full_time',
    'Maintain and improve our AWS infrastructure, CI/CD pipelines and Kubernetes clusters.',
    ARRAY['aws', 'kubernetes', 'docker', 'terraform', 'github actions'], 'en', 4500, 5800, 'month',
    now() - interval '3 days', NULL
),
(
    'tyomarkkinatori', 'seed-006', 'https://example.com/jobs/seed-006',
    'Asiakastukihenkilö, osa-aikainen', 'Oulun Palvelupiste Oy', 'Oulu', 'onsite', 'part_time',
    'Osa-aikainen työ asiakastuessa, sopii hyvin opiskelijalle. Hyvä suomen ja englannin kielen taito.',
    ARRAY['customer service', 'finnish', 'english'], 'fi', 13.50, 15.00, 'hour',
    now() - interval '7 days', now() + interval '10 days'
),
(
    'duunitori', 'seed-007', 'https://example.com/jobs/seed-007',
    'Machine Learning Engineer', 'Nordic Vision AI Oy', 'Helsinki', 'remote', 'full_time',
    'Develop and deploy NLP models in production. Experience with PyTorch and vector databases appreciated.',
    ARRAY['python', 'pytorch', 'nlp', 'postgresql', 'docker'], 'en', 5000, 6500, 'month',
    now() - interval '4 days', now() + interval '3 weeks'
),
(
    'oikotie', 'seed-008', 'https://example.com/jobs/seed-008',
    'Full Stack Developer, fixed-term', 'Turun Koodi Oy', 'Turku', 'hybrid', 'temporary',
    'Six-month project building a Node.js + React application for a public sector client.',
    ARRAY['node.js', 'react', 'postgresql', 'typescript'], 'en', 3600, 4200, 'month',
    now() - interval '6 days', now() + interval '1 week'
)
ON CONFLICT (source, source_job_id) DO NOTHING;
