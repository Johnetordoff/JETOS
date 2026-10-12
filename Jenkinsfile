pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('JETOS Docker qualification') {
            steps {
                sh 'python3 jetos.py docker-test'
            }
        }
    }

    post {
        always {
            sh 'docker image rm jetos:fat-test >/dev/null 2>&1 || true'
        }
    }
}
