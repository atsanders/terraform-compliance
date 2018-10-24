import os
from argparse import ArgumentParser

try:
    from radish.main import main as call_radish
except ImportError as e:
    import subprocess
    import sys

    def pip(action, package):
        print '{}ing {}..'.format(action, package)
        subprocess.call([sys.executable, "-m", "pip", action, package])

    print "Fixing the problem on radish and radish-bdd"
    pip('uninstall', '--yes radish-bdd')
    pip('uninstall', '--yes radish')
    pip('install', 'radish')
    pip('install', 'radish-bdd')
finally:
    print "Importing radish again."
    from radish.main import main as call_radish

from tempfile import mkdtemp
from git import Repo
from terraform_compliance.common.pyhcl_helper import load_tf_files
from distutils.dir_util import copy_tree
from shutil import rmtree
from terraform_compliance.common.readable_dir import ReadableDir


__app_name__ = "terraform-compliance"
__version__ = "0.4.2"


class ArgHandling(object):
    pass

def cli():
    args = ArgHandling()
    parser = ArgumentParser(prog=__app_name__,
                            description="BDD Test Framework for Hashicorp terraform")
    parser.add_argument("--features", "-f", dest="features", metavar='feature_directory', action=ReadableDir,
                        help="Directory consists of BDD features", required=True)
    parser.add_argument("--tfdir", "-t", dest="tf_dir", metavar='terraform_directory', action=ReadableDir,
                        help="Directory (or git repository with 'git:' prefix) consists of Terraform Files",
                        required=True)
    parser.add_argument("--identity", "-i", dest="ssh_key", metavar='ssh_private_key', type=str, nargs='?',
                        help="SSH Private key that will be use on git authentication.", required=False)
    parser.add_argument("--version", "-v", action="version", version=__version__)

    _, radish_arguments = parser.parse_known_args(namespace=args)

    print('{} v{} initiated'.format(__app_name__, __version__))

    steps_directory = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'steps')
    print('Steps    : {}'.format(steps_directory))

    # SSH Key is given for git authentication
    ssh_cmd = {}
    if args.ssh_key:
        ssh_cmd = {"GIT_SSH_COMMAND": "ssh -l {} -i {}".format('git', args.ssh_key)}

    # A remote repository used here
    if args.features.startswith(('http', 'https', 'ssh')):
        features_git_repo = args.features
        args.features = mkdtemp()

        Repo.clone_from(url=features_git_repo, to_path=args.features, env=ssh_cmd)
    features_directory = os.path.join(os.path.abspath(args.features))
    print('Features : {}{}'.format(features_directory, (' ({})'.format(features_git_repo) if 'features_git_repo' in locals() else '')))

    tf_tmp_dir = mkdtemp()

    # A remote repository is used here.
    if args.tf_dir.startswith(('http', 'https', 'ssh')):
        tf_git_repo = args.tf_dir
        Repo.clone_from(url=tf_git_repo, to_path=tf_tmp_dir, env=ssh_cmd)

    # A local directory is used here
    else:
        # Copy the given local directory to another place, since we may change some tf files for compatibility.
        copy_tree(args.tf_dir, tf_tmp_dir)

    tf_directory = os.path.join(os.path.abspath(tf_tmp_dir))
    print('TF Files : {} ({})'.format(tf_directory, args.tf_dir))

    commands = ['radish',
                '--write-steps-once',
                features_directory,
                '--basedir', steps_directory,
                '--user-data=tf_dir={}'.format(tf_directory)]
    commands.extend(radish_arguments)

    load_tf_files(tf_directory)
    print('Running tests.')
    result = call_radish(args=commands[1:])

    # Delete temporary directory we created
    print('Cleaning up.')
    rmtree(tf_directory)


if __name__ == '__main__':
    cli()
