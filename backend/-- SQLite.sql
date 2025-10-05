-- SQLite
-- recent jobs
SELECT job_id, title, mandatory_skills, preferred_skills
FROM job
ORDER BY job_id DESC
LIMIT 20;

-- candidates for the latest job
SELECT candidate_id, job_id, name, email, match_score, decision, extracted_skills
FROM candidate
WHERE job_id = (SELECT MAX(job_id) FROM job)
ORDER BY candidate_id DESC;