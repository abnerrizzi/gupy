A project to scrap gupy portal.

First scrap all companies, then go to each one and extract all the jobs;

    docker run --rm -v $(pwd):/app -w /app/"$repo_dir" zricethezav/gitleaks:latest \
      detect \
      --source=/app/"$repo_dir" \
      --report-format json \
      --report-path /app/"$repo_dir".json
