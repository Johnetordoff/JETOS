pipeline {
    agent any

    stages {
        stage('JETOS Work Server cycle') {
            steps {
                // Jenkins only schedules the repository-owned work cycle.
                // JETOS decides how to build, test, and optionally improve.
                sh 'python3 tools/work_server.py run-cycle'
            }
        }
    }
}
