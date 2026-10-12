pipeline {
    agent any

    stages {
        stage('JETOS Docker qualification') {
            steps {
                sh 'python3 jetos.py docker-test'
            }
        }
    }
}
