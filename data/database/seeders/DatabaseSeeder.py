"""Database seeder — runs all seeders."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.seeding import Seeder

from database.seeders.FrameworkSeeder import FrameworkSeeder
from database.seeders.UserSeeder import UserSeeder


class DatabaseSeeder(Seeder):
    def run(self):
        self.call(UserSeeder)
        self.call(FrameworkSeeder)
